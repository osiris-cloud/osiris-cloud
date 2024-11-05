## Container Apps

### Get Apps [/container-apps/{nsid}/{appid}]

Method: `GET`

Returns: `application/json`

Parameters:

- `nsid` (string, required): The id of the namespace in which the app belongs.

- `appid` (string, optional): The id of the container app. If not provided, all app instances in the
  namespace will be returned.

Sample Request:

```bash
curl "https://osiriscloud.io/api/container-apps/default" -H "Authorization : Token <token>"
```

Sample Response:

```json
{
  "status": "success",
  "message": "Get container apps",
  "apps": [
    {
      "appid": "2e9c7656-75c4-4c34-a3c5-5a130fdad43e",
      "name": "Diving into null",
      "url": "myapp.poweredge.dev",
      "connection_port": 30121,
      "connection_protocol": "tcp",
      "state": "active",
      "restart_policy": "always",
      "created_at": "2024-10-26T22:24:28.213Z",
      "updated_at": "2024-10-26T22:24:28.213Z",
      "exposed_public": false,
      "custom_domains": [],
      "main": {
        "containerid": "2e6c7656-75c4-4c34-a3c5-5a130fdad43e",
        "image": "csaw.registry.osiriscloud.io/div:latest",
        "pull_secret": "0192efc6-7287-7353-b1c5-cca47171d6a0",
        "port": 9191,
        "port_protocol": "tcp",
        "cpu_request": 0.5,
        "memory_request": 1,
        "cpu_limit": 1,
        "memory_limit": 2
      },
      "init": {},
      "sidecar": {},
      "autoscale": {
        "enabled": true,
        "min_replicas": 1,
        "max_replicas": 5,
        "cpu_trigger": 70,
        "memory_trigger": 80
      },
      "volumes": []
    }
  ]
}
```

### Create App [/container-apps/{nsid}]

Method: `PUT`

Accepts: `application/json`

Returns: `application/json`

Parameters:

- `nsid` (string, required): The id of the namespace in which the app belongs.

Request body parameters:

- `name` (string, required): The name of the container app.


- `slug` (string, required): The unique slug of the container app. This will be used to generate the URL.

- `replicas` (int, optional): The number of instances of the app. Default is 1.

- `connection_protocol` (string, required): The connection protocol for the app. This can be `http`, `tcp` or `udp`.
  If `tcp` or `udp` is used, the app will be exposed on a random ip and port. If `http`, the app will be exposed on port
  80 and 443.


- `exposed_public` (boolean, required): If false, the app will only be accessible from the NYU network. The app will be
  public only if the `connection_protocol` is `http`.


- `custom_domains` (array, optional): This setting only applies if the `connection_protocol` is `http`. It takes 2
  fields.
    - `name` (string, required): The domain you want to use for the app.
    - `gen_cert` (bool, required): If true, a TLS certificate will be generated for the domain. The user can use a
      CNAME record to point the domain to the app.


- `autoscale` (object, optional): Autoscaling configuration for the app. Only horizontal scaling is supported at this
  time.
    - `enable` (bool, required): If true, autoscaling will be enabled.
      The sub-fields below are required only if `enabled` is set to `true`.
    - `min_replicas` (int, required): The minimum number of replicas to scale down to.
    - `max_replicas` (int, required): The maximum number of replicas to scale up to.
    - `scaleup_stb_window` (int, optional): The time window in seconds to use for the scale-up stabilization period.
      Default is 300.
    - `scaledown_stb_window` (int, optional): The time window in seconds to use for the scale-down stabilization period.
      Default is 300.
    - `cpu_trigger` (int, required): The CPU trigger percentage for scaling. New replicas will be added if the metric
      reaches this value.
    - `memory_trigger` (int, required): The memory trigger percentage for scaling. New replicas will be added if the
      metric reaches this value.

  <u>Note on scaling</u>:

  Each app will have a default of 1 replica. The app will scale up if the combined CPU or memory utilization of all
  containers reaches the trigger percentage of `cpu_request` or `memory_request` respectively.


- `main` (object, required): Main container configuration.
    - `image` (string, required): The image to use for the container.
    - `pull_secret`: (string, optional): The id of the secret to use for pulling the image.
    - `env_secret`: (string, optional): The id of the secret to use for injecting environment variables.
    - `port` (int, required): The port the container listens on.
    - `port_protocol`: (string, required): The protocol of the port. Allowed values are `tcp` and `udp`.
    - `command` (array, optional): If specified, it replaces the `ENTRYPOINT` in the Dockerfile.
    - `args` (array, optional): If specified, it replaces the `CMD` in the Dockerfile.
    - `container_port` (int, required): The port the container listens on. Only TCP ports are supported at this time.
    - `cpu_request` (int, required): The minimum guaranteed vCPU cores to allocate.
    - `memory_request` (int, required): The minimum guaranteed memory to allocate in GB.
    - `cpu_limit` (int, required): The maximum number of vCPU cores the container can use.
    - `memory_limit` (int, required): The maximum amount of memory the container can use in GB.


- `sidecar` (object, optional): Sidecar runs alongside the main container. The config is same as `main`.


- `init` (object, optional): Init container runs before the main and sidecar container. The main and sidecar containers
  starts up only after the init container exits successfully. The config is same as `main`.

  <u>Note on resources</u>:

  Autoscaling trigger will be based on the `cpu_request` and `memory_request` values. The app will scale up if the
  combined `cpu_request` or `memory_request` of all containers reaches the trigger percentage of `cpu_request` or
  `memory_request` respectively in the `autoscale` config.


- `volumes` (array, optional): Persistent Volumes to attach to the app.
    - `name` (string, required): The name of the volume.
    - `size` (int, required): The size of the volume in GB.
    - `mount_path` (string, required): The path to mount the volume in the container.
    - `mode` (string, required): The access mode for `init`, `main` and `sidecar`. Possible values are
        - `''` : An empty string represents no access.
        - `'rw'` : Read and write.
        - `'ro'`. Read only.

      An example configuration looks like this:
        ```
        "mode": {
          "init": "",
          "main": "rw",
          "sidecar": "ro"
        }
        ```

- `restart_policy` (string, optional): The restart policy for the container. Possible values
  are `always`, `on_failure`, and `never`. Default is `always`.

  <u>Restart Policy Definitions</u>

    - `always`: The container will always restart when it stops, regardless of the exit status.
    - `on_failure`: The container will restart only if it stops with a non-zero status.
    - `never`: The container will not restart on when it stops.

Sample Request:

```json
{
  "name": "LogMeIn1",
  "slug": "logmein1",
  "connection_protocol": "http",
  "state": "active",
  "restart_policy": "always",
  "exposed_public": false,
  "main": {
    "image": "058264123223.dkr.ecr.us-east-1.amazonaws.com/csaw24:logmein-webapp",
    "pull_secret": "0192efd1-881d-74a1-81e5-46c23f9be951",
    "env_secret": "0192efd1-c075-7963-8dd5-22fc45551615",
    "port": 10086,
    "port_protocol": "tcp",
    "cpu_request": 1,
    "memory_request": 2,
    "cpu_limit": 2,
    "memory_limit": 4
  },
  "autoscale": {
    "enabled": true,
    "min_replicas": 1,
    "max_replicas": 5,
    "cpu_trigger": 70,
    "memory_trigger": 80
  },
  "volumes": [
    {
      "name": "Temp",
      "size": 0.5,
      "mount_path": "/tmp",
      "mode": {
        "init": "",
        "main": "rw",
        "sidecar": ""
      }
    }
  ]
}
```

Sample Response:

```json
{
  "status": "success",
  "message": "Create container app",
  "app": {
    "appid": "0192efdc-fdd9-74c1-b5d9-816ce8c7d900",
    "name": "LogMeIn1",
    "url": "logmein1.poweredge.dev",
    "replicas": 1,
    "connection_port": 443,
    "connection_protocol": "http",
    "state": "creating",
    "restart_policy": "always",
    "created_at": "2024-10-26T22:25:20.213Z",
    "updated_at": "2024-10-26T22:27:28.203Z",
    "exposed_public": false,
    "custom_domains": [],
    "main": {
      "containerid": "0192efde-5683-70a3-8dfa-817d5acbbc1a",
      "image": "058264123223.dkr.ecr.us-east-1.amazonaws.com/csaw24:logmein-webapp",
      "pull_secret": "0192efd1-881d-74a1-81e5-46c23f9be951",
      "env_secret": "0192efd1-c075-7963-8dd5-22fc45551615",
      "port": 10086,
      "port_protocol": "tcp",
      "cpu_request": 1,
      "memory_request": 2,
      "cpu_limit": 2,
      "memory_limit": 4
    },
    "init": {},
    "sidecar": {},
    "autoscale": {
      "enabled": true,
      "min_replicas": 1,
      "max_replicas": 5,
      "cpu_trigger": 70,
      "memory_trigger": 80
    },
    "volumes": [
      {
        "volid": "0192efdf-24e7-7512-913d-f6f01d287494",
        "name": "Temp",
        "size": 0.5,
        "mount_path": "/tmp",
        "mode": {
          "init": "",
          "main": "rw",
          "sidecar": ""
        }
      }
    ]
  }
}
```

### Update App [/container-apps/{nsid}/{appid}]

Method: `PATCH`

Accepts: `application/json`

Returns: `application/json`

Parameters:

- `nsid` (string, required): The id of the namespace in which the app belongs.

Request body parameters:

- `name` (string, required): The name of the container app.


- `slug` (string, required): The unique slug of the container app. This will be used to generate the URL.


- `connection_protocol` (string, required): The connection protocol for the app. This can be `http`, `tcp` or `udp`.
  If `tcp` or `udp` is used, the app will be exposed on a random ip and port. If `http`, the app will be exposed on port
  80 and 443.


- `exposed_public` (boolean, optional): If false, the app will only be accessible from the NYU network. The app will be
  public only if the `connection_protocol` is `http`.


- `custom_domains` (array, optional): This setting only applies if the `connection_protocol` is `http`. It takes 2
  fields.
    - `name` (string, required): The domain you want to use for the app.
    - `gen_cert` (bool, required): If true, a TLS certificate will be generated for the domain. The user can use a
      CNAME record to point the domain to the app.


- `autoscale` (object, optional): Autoscaling configuration for the app. Only horizontal scaling is supported at this
  time.
    - `enable` (bool, required): If true, autoscaling will be enabled.
      The sub-fields below are required only if `enabled` is set to `true`.
    - `min_replicas` (int, required): The minimum number of replicas to scale down to.
    - `max_replicas` (int, required): The maximum number of replicas to scale up to.
    - `scaleup_stb_window` (int, optional): The time window in seconds to use for the scale-up stabilization period.
      Default is 300.
    - `scaledown_stb_window` (int, optional): The time window in seconds to use for the scale-down stabilization period.
      Default is 300.
    - `cpu_trigger` (int, required): The CPU trigger percentage for scaling. New replicas will be added if the metric
      reaches this value.
    - `memory_trigger` (int, required): The memory trigger percentage for scaling. New replicas will be added if the
      metric reaches this value.


- `main` (object, required): Main container configuration.
    - `image` (string, required): The image to use for the container.
    - `pull_secret`: (string, optional): The id of the secret to use for pulling the image.
    - `env_secret`: (string, optional): The id of the secret to use for injecting environment variables.
    - `port` (int, required): The port the container listens on.
    - `port_protocol`: (string, required): The protocol of the port. Allowed values are `tcp` and `udp`.
    - `command` (array, optional): If specified, it replaces the `ENTRYPOINT` in the Dockerfile.
    - `args` (array, optional): If specified, it replaces the `CMD` in the Dockerfile.
    - `container_port` (int, required): The port the container listens on. Only TCP ports are supported at this time.
    - `cpu_request` (int, required): The minimum guaranteed vCPU cores to allocate.
    - `memory_request` (int, required): The minimum guaranteed memory to allocate in GB.
    - `cpu_limit` (int, required): The maximum number of vCPU cores the container can use.
    - `memory_limit` (int, required): The maximum amount of memory the container can use in GB.


- `sidecar` (object, optional): Sidecar runs alongside the main container. The config is same as `main`.


- `init` (object, optional): Init container runs before the main and sidecar container. The main and sidecar containers
  starts up only after the init container exits successfully. The config is same as `main`.


- `volumes` (array, optional): Persistent Volumes to attach to the app.
    - `name` (string, required): The name of the volume.
    - `mount_path` (string, required): The path to mount the volume in the container.
    - `mode` (string, required): The access mode for `init`, `main` and `sidecar`. Possible values are
        - `''` : An empty string represents no access.
        - `'rw'` : Read and write.
        - `'ro'`. Read only.

- `restart_policy` (string, optional): The restart policy for the container. Possible values
  are `always`, `on_failure`, and `never`. Default is `always`.

Sample Request:

```json
{
  "custom_domains": [
    {
      "name": "logmein1.ctf.csaw.io",
      "gen_cert": true
    }
  ]
}
```

Sample Response:

```json
{
  "status": "success",
  "message": "Update container app",
  "app": {
    "appid": "0192efdc-fdd9-74c1-b5d9-816ce8c7d900",
    "name": "LogMeIn1",
    "url": "logmein1.poweredge.dev",
    "replicas": 1,
    "connection_port": 443,
    "connection_protocol": "http",
    "state": "creating",
    "restart_policy": "always",
    "created_at": "2024-10-26T22:25:20.213Z",
    "updated_at": "2024-10-26T22:27:28.203Z",
    "exposed_public": false,
    "custom_domains": [
      {
        "name": "logmein1.ctf.csaw.io",
        "gen_cert": true
      }
    ],
    "main": {
      "containerid": "0192efde-5683-70a3-8dfa-817d5acbbc1a",
      "image": "058264123223.dkr.ecr.us-east-1.amazonaws.com/csaw24:logmein-webapp",
      "pull_secret": "0192efd1-881d-74a1-81e5-46c23f9be951",
      "env_secret": "0192efd1-c075-7963-8dd5-22fc45551615",
      "port": 10086,
      "port_protocol": "tcp",
      "cpu_request": 1,
      "memory_request": 2,
      "cpu_limit": 2,
      "memory_limit": 4
    },
    "init": {},
    "sidecar": {},
    "autoscale": {
      "enabled": true,
      "min_replicas": 1,
      "max_replicas": 5,
      "cpu_trigger": 70,
      "memory_trigger": 80
    },
    "volumes": [
      {
        "volid": "0192efdf-24e7-7512-913d-f6f01d287494",
        "name": "Temp",
        "size": 0.5,
        "mount_path": "/tmp",
        "mode": {
          "init": "",
          "main": "rw",
          "sidecar": ""
        }
      }
    ]
  }
}
```

### Delete App [/container-apps/{nsid}/{appid}]

Method: `DELETE`

Returns: `application/json`

Parameters:

- `nsid` (string, required): The id of the namespace in which the app belongs.

- `appid` (string, required): The id of the container app.

Sample Request:

```bash
curl -X DELETE "https://osiriscloud.io/api/container-apps/default/0192d5cc-b85d-76e2-9c5f-3404c9911673" -H "Token: <token>"
```

Sample Response:

```json
{
  "status": "success",
  "message": "Delete container app"
}
```

## Additional Functions

### Redeploy App [/container-apps/{nsid}/{appid}/redeploy]

Stops all current replicas and starts a new instances of the app. This does not affect existing volumes, if any.

Method: `POST`

Returns: `application/json`

Sample Response:

```json
{
  "status": "success",
  "message": "Redeploy container app"
}
```

### App Logs [/container-apps/{nsid}/{appid}/logs]

Method: `POST`

Returns: `application/json`

Sample Response:

```json
{
  "status": "success",
  "message": "Get container app logs",
  "logs": {
    "main": {
      "replica": 1,
      "logs": [
        "2024-10-27T12:45:01.000000Z Starting application...",
        "2024-10-27T12:45:02.000000Z Connecting to database...",
        "2024-10-27T12:45:10.000000Z Handling request from 192.168.1.1",
        "2024-10-27T12:45:15.000000Z Sending response to client",
        "2024-10-27T12:45:20.000000Z Closing database connection."
      ]
    }
  }
}
```
