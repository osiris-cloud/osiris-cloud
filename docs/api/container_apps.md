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
  "app": {
    "appid": "0194c459-6497-7680-84eb-6da1aebf9018",
    "name": "Nginx",
    "url": "https://nginx1.poweredge.dev",
    "connection_port": 443,
    "connection_protocol": "http",
    "custom_domains": [],
    "main": {
      "containerid": "0194c459-6494-78d2-b049-6c2252659d96",
      "image": "nginx:latest",
      "pull_secret": null,
      "env_secret": null,
      "port": 80,
      "port_protocol": "tcp",
      "command": [],
      "args": [],
      "cpu": 0.25,
      "memory": 0
    },
    "init": {},
    "sidecar": {},
    "volumes": [],
    "scaling": {
      "min_replicas": 1,
      "max_replicas": 1,
      "scaleup_stb_window": 0,
      "scaledown_stb_window": 150,
      "scalers": []
    },
    "created_at": "2025-02-02T01:49:40.374Z",
    "updated_at": "2025-02-02T01:49:40.378Z"
  },
  "message": "Create container app"
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


- `update_strategy` (string, optional): The update strategy for the app. Possible values are `recreate` and `rolling`.


- `connection_protocol` (string, required): The connection protocol for the app. This can be `http`, `tcp` or `udp`.
  If `tcp` or `udp` is used, the app will be exposed on a random port. If `http`, the app will be available on a
  subdomain and on port 80 and 443. This cannot be changed once set.


- `firewall` (object, optional): Firewall configuration for the app.
    - `precedence` (string, required): The precedence of the firewall rule. You can set it to `allow` or `deny`.
    - `allow` (array, required): The list of CIDR blocks to allow traffic from.
    - `deny` (array, required): The list of CIDR blocks to deny traffic from.
    - `nyu_only` (array, optional): If true, the app will only be accessible from the NYU network.


- `ingress` (object, optional): Ingress configuration for the app. This setting only applies to web apps.
    - `hosts` (array, required): The list of custom domains to use for the app.
    - `pass_tls` (boolean, required): If `true`, TLS auth will be passed to the app, instead of the platform handling it.


- `scaling` (object, optional): Horizontal scaling configuration for the app.
    - `min_replicas` (int, required): The minimum number of replicas available at all times.
    - `max_replicas` (int, required if scalers are present): The maximum number of replicas to scale up to.
    - `scaledown_stb_window` (int, optional): The time window in seconds to use for the scale-down stabilization period.
      Default is 300 (5 mins).
    - `scalers` (array, required): The metrics to use for scaling. The metrics are defined as objects with the following
      fields:
        - `type` (string, required): The type of metric. Possible values are `cpu` and `memory`.
        - `target` (int, required): The trigger percentage for scaling. New replicas will be added if the metric
          reaches this value.


- `main` (object, required): Main container configuration.
    - `image` (string, required): The image to use for the container.
    - `pull_secret`: (string, optional): The id of the secret to use for pulling the image.
    - `env_secret`: (string, optional): The id of the secret to use for injecting environment variables.
    - `command` (array, optional): If specified, it replaces the `ENTRYPOINT` in the Dockerfile.
    - `args` (array, optional): If specified, it replaces the `CMD` in the Dockerfile.
    - `port` (int, required for main): The port the container listens on. Only TCP ports are supported at this time.
    - `port_protocol`: (string, required): The protocol of the port. Allowed values are `tcp` and `udp`.
    - `cpu` (int, required): The number of CPU cores to allocate.
    - `memory` (int, required): The amount of memory to allocate in GB.


- `sidecar` (object, optional): Sidecar runs alongside the main container. The config is same as `main`.


- `init` (object, optional): Init container runs before the main and sidecar container. The main and sidecar containers
  starts up only after the init container exits successfully. The config is same as `main`.


- `volumes` (array, optional): Persistent Volumes to attach to the app.
    - `name` (string, required): The name of the volume.
    - `type` (string, required): Available types are
        - `fs` : Filesystem: A volume that can be mounted to a container as a directory.
        - `temp` : Temporary: An ultra-fast temp volume that can be mounted to a container as a directory.
        - `block` : Block Device: A volume that can be mounted to a container as a block device.
        - `secret` : Secret: A volume that can be mounted to a container as a read-only file containing secret values.
    - `secretid` (string, optional): The id of the secret to use for the volume. Required only if the volume type
      is `secret`.
    - `size` (int, required): The size of the volume in GiB. This can be expanded later.
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
      <u>Note</u>
        - For `secret` type volumes, the `mode` type can only be `ro` or `''`.
        - For `block` type volumes, the `mode` type can only be `rw` or `''`.

- `firewall` (object, optional): Firewall configuration for the app.
    - `precedence` (string, required): The precedence of the firewall rule. You can set it to `allow` or `deny`.
    - `allow` (array, required): The list of IP address, IP ranges and subnets to allow traffic from.
    - `deny` (array, required): The list of IP address, IP ranges and subnets to deny traffic from.
    - `nyu_only` (array, optional): If true, the app will only be accessible from the NYU network.

Sample Request:

```json
{
  "name": "nginx",
  "slug": "nginx",
  "connection_protocol": "http",
  "update_strategy": "recreate",
  "main": {
    "type": "main",
    "image": "nginx:latest",
    "port": 80,
    "port_protocol": "tcp",
    "cpu": 0.25,
    "memory": 0.5
  },
  "sidecar": {},
  "init": {},
  "volumes": [
    {
      "type": "temp",
      "name": "Temp",
      "size": 0.1,
      "mount_path": "/tmp",
      "mode": {
        "init": "",
        "main": "rw",
        "sidecar": ""
      }
    }
  ],
  "scaling": {
    "min_replicas": 1
  },
  "firewall": {
    "precedence": "deny",
    "allow": [
      "0.0.0.0/0"
    ],
    "deny": [],
    "nyu_only": false
  }
}
```

Sample Response:

```json
{
  "status": "success",
  "app": {
    "appid": "0195b0e9-987a-74e2-b686-f0a7e8c846e3",
    "name": "nginx",
    "url": "https://nginx.poweredge.dev",
    "connection_port": 443,
    "connection_protocol": "http",
    "state": "creating",
    "update_strategy": "recreate",
    "main": {
      "image": "nginx:latest",
      "native_image": false,
      "pull_secret": null,
      "env_secret": null,
      "port": 80,
      "port_protocol": "tcp",
      "command": [],
      "args": [],
      "cpu": 0.25,
      "memory": 0.5
    },
    "init": {},
    "sidecar": {},
    "volumes": [
      {
        "volid": "0195b0e9-9878-72b0-b89a-84dc1f11b369",
        "type": "temp",
        "name": "Temp",
        "size": 0.1,
        "mount_path": "/tmp",
        "mode": {
          "init": "",
          "main": "rw",
          "sidecar": ""
        }
      }
    ],
    "scaling": {
      "min_replicas": 1,
      "max_replicas": 1,
      "scaleup_stb_window": 0,
      "scaledown_stb_window": 150,
      "scalers": []
    },
    "ingress": {
      "pass_tls": false,
      "hosts": []
    },
    "firewall": {
      "deny": [],
      "allow": [
        "0.0.0.0/0"
      ],
      "precedence": "deny",
      "nyu_only": false
    },
    "created_at": "2025-03-20T00:17:33.818Z",
    "updated_at": "2025-03-20T00:17:33.819Z"
  },
  "message": "Create container app"
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


- `update_strategy` (string, optional): The update strategy for the app. Possible values are `recreate` and `rolling`.


- `connection_protocol` (string, required): The connection protocol for the app. This can be `http`, `tcp` or `udp`.
  If `tcp` or `udp` is used, the app will be exposed on a random port. If `http`, the app will be available on a
  subdomain and on port 80 and 443. This cannot be changed once set.


- `firewall` (object, optional): Firewall configuration for the app.
    - `precedence` (string, required): The precedence of the firewall rule. You can set it to `allow` or `deny`.
    - `allow` (array, required): The list of CIDR blocks to allow traffic from.
    - `deny` (array, required): The list of CIDR blocks to deny traffic from.
    - `nyu_only` (array, optional): If true, the app will only be accessible from the NYU network.


- `ingress` (object, optional): Ingress configuration for the app. This setting only applies to web apps.
    - `hosts` (array, required): The list of custom domains to use for the app.
    - `pass_tls` (boolean, required): If `true`, TLS auth will be passed to the app, instead of the platform handling it.


- `scaling` (object, optional): Horizontal scaling configuration for the app.
    - `min_replicas` (int, required): The minimum number of replicas available at all times.
    - `max_replicas` (int, required if scalers are present): The maximum number of replicas to scale up to.
    - `scaledown_stb_window` (int, optional): The time window in seconds to use for the scale-down stabilization period.
      Default is 300 (5 mins).
    - `scalers` (array, required): The metrics to use for scaling. The metrics are defined as objects with the following
      fields:
        - `type` (string, required): The type of metric. Possible values are `cpu` and `memory`.
        - `target` (int, required): The trigger percentage for scaling. New replicas will be added if the metric
          reaches this value.


- `main` (object, required): Main container configuration.
    - `image` (string, required): The image to use for the container.
    - `pull_secret`: (string, optional): The id of the secret to use for pulling the image.
    - `env_secret`: (string, optional): The id of the secret to use for injecting environment variables.
    - `command` (array, optional): If specified, it replaces the `ENTRYPOINT` in the Dockerfile.
    - `args` (array, optional): If specified, it replaces the `CMD` in the Dockerfile.
    - `port` (int, required for main): The port the container listens on. Only TCP ports are supported at this time.
    - `port_protocol`: (string, required): The protocol of the port. Allowed values are `tcp` and `udp`.
    - `cpu` (int, required): The number of CPU cores to allocate.
    - `memory` (int, required): The amount of memory to allocate in GB.


- `sidecar` (object, optional): Sidecar runs alongside the main container. The config is same as `main`.


- `init` (object, optional): Init container runs before the main and sidecar container. The main and sidecar containers
  starts up only after the init container exits successfully. The config is same as `main`.


- `volumes` (array, optional): Persistent Volumes to attach to the app.
    - `name` (string, required): The name of the volume.
    - `type` (string, required): Available types are
        - `fs` : Filesystem: A volume that can be mounted to a container as a directory.
        - `temp` : Temporary: An ultra-fast temp volume that can be mounted to a container as a directory.
        - `block` : Block Device: A volume that can be mounted to a container as a block device.
        - `secret` : Secret: A volume that can be mounted to a container as a read-only file containing secret values.
    - `secretid` (string, optional): The id of the secret to use for the volume. Required only if the volume type
      is `secret`.
    - `size` (int, required): The size of the volume in GiB. This can be expanded later.
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
      <u>Note</u>
        - For `secret` type volumes, the `mode` type can only be `ro` or `''`.
        - For `block` type volumes, the `mode` type can only be `rw` or `''`.

- `firewall` (object, optional): Firewall configuration for the app.
    - `precedence` (string, required): The precedence of the firewall rule. You can set it to `allow` or `deny`.
    - `allow` (array, required): The list of IP address, IP ranges and subnets to allow traffic from.
    - `deny` (array, required): The list of IP address, IP ranges and subnets to deny traffic from.
    - `nyu_only` (array, optional): If true, the app will only be accessible from the NYU network.

Sample Request:

```json
{
    "name": "nginx",
    "update_strategy": "recreate",
    "main": {
        "type": "main",
        "image": "nginx:latest",
        "port": 80,
        "port_protocol": "tcp",
        "cpu": 0.25,
        "memory": 0.5
    },
    "volumes": [
        {
            "type": "temp",
            "name": "Temp",
            "size": 0.1,
            "mount_path": "/tmp",
            "mode": {
                "init": "",
                "main": "rw",
                "sidecar": ""
            },
            "volid": "0195b0e9-9878-72b0-b89a-84dc1f11b369"
        }
    ],
    "scaling": {
        "min_replicas": 1,
        "max_replicas": 2,
        "scaleup_stb_window": 0,
        "scaledown_stb_window": 300,
        "scalers": [
            {
                "type": "cpu",
                "target": 70
            },
            {
                "type": "memory",
                "target": 70
            }
        ]
    },
    "ingress": {
        "hosts": [
            "mysite.example.con"
        ],
        "pass_tls": false
    }
}
```

Sample Response:

```json
{
    "status": "success",
    "app": {
        "appid": "0195b0e9-987a-74e2-b686-f0a7e8c846e3",
        "name": "nginx",
        "url": "https://nginx.poweredge.dev",
        "connection_port": 443,
        "connection_protocol": "http",
        "state": "created",
        "update_strategy": "recreate",
        "main": {
            "image": "nginx:latest",
            "native_image": false,
            "pull_secret": null,
            "env_secret": null,
            "port": 80,
            "port_protocol": "tcp",
            "command": [],
            "args": [],
            "cpu": 0.25,
            "memory": 0.5
        },
        "init": {},
        "sidecar": {},
        "volumes": [
            {
                "volid": "0195b0e9-9878-72b0-b89a-84dc1f11b369",
                "type": "temp",
                "name": "Temp",
                "size": 0.1,
                "mount_path": "/tmp",
                "mode": {
                    "init": "",
                    "main": "rw",
                    "sidecar": ""
                }
            }
        ],
        "scaling": {
            "min_replicas": 1,
            "max_replicas": 1,
            "scaleup_stb_window": 0,
            "scaledown_stb_window": 150,
            "scalers": []
        },
        "ingress": {
            "pass_tls": false,
            "hosts": [
                "mysite.example.con"
            ]
        },
        "firewall": {
            "deny": [],
            "allow": [
                "0.0.0.0/0"
            ],
            "precedence": "deny",
            "nyu_only": false
        },
        "created_at": "2025-03-20T00:17:33.818Z",
        "updated_at": "2025-03-20T00:22:14.117Z"
    },
    "message": "Update container app"
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


### Restart App [/container-apps/{nsid}/{appid}/restart]

Stops all current replicas and starts a new instances of the app. This does not affect existing volumes, if any.

Method: `POST`

Returns: `application/json`

Sample Response:

```json
{
  "status": "success",
  "message": "Restart container app"
}
```
