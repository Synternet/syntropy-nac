![Tests](https://github.com/SyntropyNet/syntropy-nac/workflows/Tests/badge.svg)
![PyPi](https://github.com/SyntropyNet/syntropy-nac/workflows/PyPi/badge.svg)

# Syntropy NAC
Syntropy Network As Code library and command line utility. 

More information can be found at https://docs.syntropystack.com/docs/network-as-code

## Requirements.

Python 3.6+

## Installation & Usage
### pip install

The latest package can be installed from PyPi:

```sh
pip install syntropynac
```


## Command line tool usage

In order to be able to export or configure networks using YAML/JSON configuration files you can use `syntropynac` utility.
First you must set proper environment variables:

```sh
$ export SYNTROPY_API_SERVER={Syntropy Stack API URL}
$ export SYNTROPY_API_TOKEN={API authorization token}
```

In case you have a registered user on the platform you can retrieve the API token using this command(deprecated and requires `syntropyctl` to be installed using pip):

```sh
$ syntropyctl login {user name} {password}
{your API authorization token}
```

You can omit `{password}` on the command line, then the utility will ask you to type the password.

In case you are using SSO to login to the platform the API authorization token can be retrieved from the Platform itself.

Or you can set the `SYNTROPY_API_TOKEN` environment variable like this(Set `SYNTROPY_API_SERVER` to the server address and `SYNTROPY_API_TOKEN` to empty value before that):

```sh
export SYNTROPY_API_TOKEN=`syntropyctl login {user name} {password}`
```

You can learn about the types of actions this utility can perform by running:

```sh
$ syntropynac --help
Usage: syntropynac [OPTIONS] COMMAND [ARGS]...

  Syntropy Network As Code cli tool

Options:
  --help  Show this message and exit.

Commands:
  configure-networks  Configure networks using a configuration YAML/JSON...
  export-networks     Exports existing networks to configuration YAML/JSON...
```

## Exporting and configuring networks

It is possible to export existing networks using `syntropynac export-networks` command which will output existing networks configuration to stdout
in a YAML format.
This configuration can be passed to `syntropynac configure-networks {infrastructure.yaml}` to create networks and connections.

Note, however, that `export-networks` command will export `connections`(if any) as well as `endpoints`. The exported `endpoints` represent the endpoints without connections along with their services and tags. Those `endpoints` are ignored by the `configure-networks` command.

Below you can find a sample configuration file for different types of networks:

```yaml
---
# Create point-to-point connections
name: interconnect
# Network topology is mandaroty. Values: P2P, P2M, MESH
topology: p2p
# Network state is mandatory. Values: present, absent
state: present
# Connections to create
connections:
  # Endpoint can be refferred to by name and by id
  endpoint-1:
    # state is present by default
    state: present
    # type is endpoint by default. Values: endpoint, tag, id
    type: endpoint
    # services specifies what services to enable for given endpoint
    services: 
    - nginx
    # id has precedence before name when type is endpoint
    id: 123
    connect_to:
      endpoint-2:
        type: endpoint
        services: 
        - postgre
  3:
    connect_to:
      endpoint-4:
        type: endpoint
    state: present
    type: id
  endpoint-5:
    connect_to:
      6:
        type: id
    state: absent
    type: endpoint

---
# Connect mqtt server with iot devices 
name: iot-network
state: present
topology: p2m
connections:
  mqtt-server-name.com:
    type: endpoint
    connect_to:
      # Will connect mqtt server with all the endpoints tagged as "iot-devices"
      iot-devices:
        state: present
        type: tag

---
# Create DNS servers mesh network 
name: dns-mesh
state: present
topology: mesh
connections:
  # Will create a mesh network using endpoints tagged as "dns-servers"
  dns-servers:
    state: present
    type: tag

---
# Delete a network
name: old-iot-network
topology: mesh
state: absent
```

