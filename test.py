import yaml
import troposphere
import troposphere.ec2 as ec2

config = yaml.load(open('test.yaml'))

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
      'Tags': [
        {'Key': 'Name', 'Value': name},
        {'Key': 'jungler-type', 'Value': node_type['tag']},
      ],
      'SecurityGroupIds': node_type['security_groups'],
      'SubnetId': node_type['subnet'],
    }

    template.add_resource(ec2.Instance(name, **params))

print(template.to_json())
