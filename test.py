import yaml
import glob
import os
import re
import tempfile
import time

import boto.cloudformation
import boto.ec2
import collections
import paramiko
import troposphere
import troposphere.ec2 as ec2


config = yaml.load(open('test.yaml'))
stack_name = 'test'

class DictFallback(object):
    def __init__(self, *dicts):
        self.dicts = dicts

    def __getitem__(self, key):
        for adict in self.dicts:
            try:
                value = adict[key]
                return value
            except KeyError:
                pass

        raise KeyError

    def get(self, key, default):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

template = troposphere.Template()

for node_type in config['cluster']:
  node_type = DictFallback(node_type, config)

  for i in range(1, node_type.get('count', 1) + 1):
    name = "%s%d" % (node_type['tag'], i)
    params = {
      'ImageId': node_type['ami'],
      'InstanceType': node_type['type'],
      'KeyName': node_type['key_pair'],
      'Tags': [
        {'Key': 'Name', 'Value': name},
        {'Key': 'jungler-type', 'Value': node_type['tag']},
      ],
      'SecurityGroupIds': node_type['security_groups'],
      'SubnetId': node_type['subnet'],
    }

    template.add_resource(ec2.Instance(name, **params))

def get_scripts(stage):
    """
    Returns a dictionary of script names keyed by server type
    """
    scripts = sorted(glob.glob('scripts/*/%s/*' % stage))
    server_scripts = collections.defaultdict(list)
    for script in scripts:
        server = re.match('scripts/([^/]+)/.*', script).group(1)
        server_scripts[server].append(script)

    return server_scripts

def run_scripts(stage, instance_data):
    """
    Executes all scripts for the given stage on a set of instances
    """
    scripts = get_scripts(stage)
    for server_type, scripts in scripts.iteritems():
        if server_type != 'local':
            # Connect to each server
            for server_name, server in instance_data[server_type].items():
                print('Connecting to %s...' % server_name)
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.load_system_host_keys()
                ssh.connect(server['hostname'], username='ubuntu',
                        look_for_keys=False)

                for script in scripts:
                    script = os.path.join(os.getcwd(), script)
                    print('Executing %s on %s...' %
                            (script.split('/')[-1], server_name))

                    # Copy the script to the machine
                    _, stdout, _ = ssh.exec_command('mktemp')
                    tempfile = stdout.readline()
                    chan = ssh.get_transport().open_session()
                    chan.exec_command('cat - > %s' % tempfile)
                    chan.send(open(script).read())
                    chan.shutdown_write()
                    ssh.exec_command('chmod +x %s' % tempfile)

                    # Actually execute the command
                    chan = ssh.get_transport().open_session()
                    chan.exec_command('env %s %s' %
                      (env_string(instance_data), tempfile))
                    if chan.recv_exit_status() != 0:
                      print("\n".join(chan.makefile_stderr().readlines()))
                      raise Exception('Command failed')

            ssh.close()
        else:
            # TODO Execute commands locally
            pass

def env_string(instance_data):
    env = {}
    for server_type, servers in instance_data.iteritems():
        env['%s_COUNT' % server_type.upper()] = len(servers)

        for name, server in servers.iteritems():
          num = int(re.split('([0-9]+)$', name)[-2])
          env['%s_%d_IP' % (server_type.upper(), num)] = server['ip']

    env_string = ' '.join('%s=%s' % (key, value) for key, value in env.iteritems())

    return env_string

#run_scripts('before-provision')

cf = boto.cloudformation.connect_to_region('us-east-1')

stack_name = '%s-%d' % (stack_name, int(time.time()))
print('Creating stack %s...' % stack_name)
cf.create_stack(stack_name, template.to_json())

print('Waiting for stack...')
while True:
    stack = cf.describe_stacks(stack_name)[0]
    if stack.stack_status == 'CREATE_COMPLETE':
      break
    elif stack.stack_status != 'CREATE_IN_PROGRESS':
      exit(1)
    time.sleep(10)

ec2 = boto.ec2.connection.EC2Connection()

resources = cf.describe_stack_resources(stack_name)
instance_ids = {resource.logical_resource_id: resource.physical_resource_id
                  for resource in resources}
instance_data = collections.defaultdict(dict)
for reservation in ec2.get_all_instances(instance_ids.values()):
  instance_data[reservation.instances[0].tags['jungler-type']] \
    [reservation.instances[0].tags['Name']] = {
      'ip': reservation.instances[0].private_ip_address,
      'instance_id': reservation.instances[0].id,
      'hostname': reservation.instances[0].public_dns_name,
    }

run_scripts('after-provision', instance_data)
