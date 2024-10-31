## Container Apps

### Get Apps [/container-apps/{nsid}/{appid}]

Method: `GET`

Returns: `application/json`

Parameters:

- `nsid` (string, required): The id of the namespace in which the registry belongs.

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
  "message": "Get container app",
  "apps": [
    {
      "name": "My App",
      "state": "active",
      "exposed_public": true,
      "appid": "2e9c7656-75c4-4c34-a3c5-5a130fdad43e",
      "created_at": "2024-10-26T22:24:28.213Z",
      "updated_at": "2024-10-26T22:24:28.213Z",
      "url": "myapp.poweredge.dev",
      "connection_protocol": "http",
      "secretid_ref": "0192d47c-264c-7f11-980a-018916d83ed0",
      "custom_domains": [
        {
          "name": "myapp.com",
          "tls_cert": true
        }
      ],
      "autoscale": {
        "enabled": true,
        "type": "horizontal",
        "metric_type": "utilization",
        "replicas": 1,
        "config": {
          "scaleup_stb_window": 300,
          "scaledown_stb_window": 300,
          "trigger": 70,
          "min": 1,
          "max": 5
        }
      },
      "volumes": [
        {
          "name": "Data Volume",
          "size": 5,
          "mount_path": "/data"
        }
      ],
      "container": {
        "name": "Frontend",
        "image": "myapp.registry.osiriscloud.io/frontend:latest",
        "image_auth_secretid_ref": "8006ff04-f15f-40fe-82ca-5db1b0fcf0cd",
        "restart_policy": "always",
        "command": [
          "npm",
          "start"
        ],
        "container_port": 80,
        "resources": {
          "cpu": 1,
          "memory": 2
        }
      }
    }
  ]
}
```

### Create App [/container-apps/{nsid}]

Method: `PUT`

Accepts: `application/json`

Returns: `application/json`

Parameters:

- `nsid` (string, required): The id of the namespace in which the registry belongs.

Request body parameters:

- `name` (string, required): The name of the container app.
- `slug` (string, required): The slug of the container app. This will be used to generate the URL.
- `nyu_net_only:` (boolean, optional): If true, the app will only be accessible from the NYU network. Default
  is `false`.
- `connection_protocol` (string, required): The connection protocol for the app. This can be `http` or `tcp`. If `tcp`
  is selected, the app will be exposed on a random port. If `http`, the app will be exposed on port 80 and 443.
- `secretid_ref` (string, optional): The id of the secret to use for the app. Secrets will be injected into the app as
  environment variables.
- `custom_domains` (array, optional): This setting only applies if the `connection_protocol` is `http`. It takes 2
  fields.
    - `name` (string, required): The domain you want to use for the app.
    - `tls_cert` (bool, required): If true, a TLS certificate will be generated for the domain. The user can use a
      CNAME record to point the domain to the app.
- `autoscale` (object, optional): Autoscaling configuration for the app.
    - `enabled` (bool, required): If true, autoscaling will be enabled.
    - `type` (string, required): The type of autoscaling. Only `horizontal` is supported at this time.
    - `metric_type` (string, required): The metric to use for autoscaling. Only `utilization` is supported at this time.
        - `config` (object, required): Autoscaling configuration.
            - `scaleup_stb_window` (int, optional): The time window to use for the scale-up stabilization period.
              Default is 300.
            - `scaledown_stb_window` (int, optional): The time window to use for the scale-down stabilization period.
              Default is 300.
            - `trigger` (int, required): The trigger percentage for scaling. New replicas will be added if the metric
              reaches this value.
            - `min` (int, required): The minimum number of replicas.
            - `max` (int, required): The maximum number of replicas.
- `volumes` (array, optional): Volumes to attach to the app.
    - `name` (string, required): The name of the volume.
    - `size` (int, required): The size of the volume in GB.
    - `mount_path` (string, required): The path to mount the volume in the container.

- `container` (object, required): Container configuration.
    - `image` (string, required): The image to use for the container.
    - `image_auth_secretid_ref` (string, optional): The id of the secret to use for pulling the image.
    - `restart_policy` (string, optional): The restart policy for the container. Possible values
      are `always`, `on_failure`,
      and `never`. Default is `always`.
    - `command` (array, optional): If specified, it replaces the `ENTRYPOINT` in the Dockerfile.
    - `args` (array, optional): If specified, it replaces the `CMD` in the Dockerfile.
    - `container_port` (int, required): The port the container listens on. Only TCP ports are supported at this time.
    - `resources` (object, required): Resources allocated for the container.
        - `cpu` (int, required): The number of vCPU cores to allocate.
        - `memory` (int, required): The amount of memory to allocate in GB.

<u>Restart Policy Definitions</u>:

- `always`: The container will always restart when it stops, regardless of the exit status.
- `on_failure`: The container will restart only if it stops with a non-zero status.
- `never`: The container will not restart on when it stops.

Sample Request:

```json
{
  "appid": "0192d5cc-b85d-76e2-9c5f-3404c9911673",
  "name": "Diving into Null",
  "slug": "null",
  "connection_protocol": "tcp",
  "autoscale": {
    "enabled": true,
    "type": "horizontal",
    "metric_type": "utilization",
    "config": {
      "trigger": 80,
      "min": 1,
      "max": 5
    }
  },
  "container": {
    "image": "null.registry.osiriscloud.io/diving-into-null:latest",
    "image_auth_secretid": "8006ff04-f15f-40fe-82ca-5db1b0fcf0cd",
    "container_port": 9191,
    "resources": {
      "cpu": 1,
      "memory": 2
    }
  }
}
```

Sample Response:

```json
{
  "name": "Diving into Null",
  "url": "null.poweredge.dev",
  "connection_protocol": "tcp",
  "connection_port": 31089
}
```

### Update App [/container-apps/{nsid}/{appid}]

Method: `PATCH`

Accepts: `application/json`

Returns: `application/json`

Parameters:

- `nsid` (string, required): The id of the namespace in which the registry belongs.

Request body parameters:

- `name` (string, required): The name of the container app.
- `nyu_net_only:` (boolean, optional): If true, the app will only be accessible from the NYU network. Default
  is `false`.
- `secretid_ref` (string, optional): The id of the secret to use for the app. Secrets will be injected into the app as
  environment variables.
- `custom_domains` (array, optional): This setting only applies if the `connection_protocol` is `http`. It takes 2
  fields.
    - `name` (string, required): The domain you want to use for the app.
    - `tls_cert` (bool, required): If true, a TLS certificate will be generated for the domain. The user can use a
      CNAME record to point the domain to the app.
- `autoscale` (object, optional): Autoscaling configuration for the app.
    - `enabled` (bool, required): If true, autoscaling will be enabled.
    - `type` (string, required): The type of autoscaling. Only `horizontal` is supported at this time.
    - `metric_type` (string, required): The metric to use for autoscaling. Only `utilization` is supported at this time.
        - `config` (object, required): Autoscaling configuration.
            - `scaleup_stb_window` (int, optional): The time window to use for the scale-up stabilization period.
              Default is 300.
            - `scaledown_stb_window` (int, optional): The time window to use for the scale-down stabilization period.
              Default is 300.
            - `trigger` (int, required): The trigger percentage for scaling. New replicas will be added if the metric
              reaches this value.
            - `min` (int, required): The minimum number of replicas.
            - `max` (int, required): The maximum number of replicas.
- `volumes` (array, optional): Volumes to attach to the app.
    - `name` (string, required): The name of the volume.
    - `size` (int, required): The size of the volume in GB.
    - `mount_path` (string, required): The path to mount the volume in the container.

- `container` (object, required): Container configuration.
    - `image` (string, required): The image to use for the container.
    - `image_auth_secretid_ref` (string, optional): The id of the secret to use for pulling the image.
    - `command` (array, optional): If specified, it replaces the `ENTRYPOINT` in the Dockerfile.
    - `args` (array, optional): If specified, it replaces the `CMD` in the Dockerfile.
    - `container_port` (int, required): The port the container listens on. Only TCP ports are supported at this time.
    - `resources` (object, required): Resources allocated for the container.
        - `cpu` (int, required): The number of vCPU cores to allocate.
        - `memory` (int, required): The amount of memory to allocate in GB.

Sample Request:

```json
{
  "autoscale": {
    "enabled": true,
    "type": "horizontal",
    "metric_type": "utilization",
    "config": {
      "trigger": 50,
      "min": 1,
      "max": 10
    }
  }
}
```

Sample Response:

```json
{
  "status": "success",
  "message": "Update container app"
}
```

### Delete App [/container-apps/{nsid}/{appid}]

Method: `DELETE`

Returns: `application/json`

Parameters:

- `nsid` (string, required): The id of the namespace in which the registry belongs.

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
  "logs": [
    {
      "replica": 1,
      "logs": [
        "2024-10-27T12:45:01.000000Z Starting application...",
        "2024-10-27T12:45:02.000000Z Connecting to database...",
        "2024-10-27T12:45:10.000000Z Handling request from 192.168.1.1",
        "2024-10-27T12:45:15.000000Z Sending response to client",
        "2024-10-27T12:45:20.000000Z Closing database connection."
      ]
    }
  ]
}
```

### App Metrics [/container-apps/{nsid}/{appid}/metrics]

Method: `POST`

Returns: `application/json`

Sample Response:

```json
{
  "status": "success",
  "message": "Redeploy container app",
  "metrics": {
    "timestamp": "2024-10-27T12:45:00Z",
    "window": "30s",
    "cpu": "25m",
    "memory": "64Mi"
  }
}
```
