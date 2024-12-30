## Container Registry

### Get Registry [/container-registry/{nsid}/{crid}]

Method: `GET`

Returns: `application/json`

Parameters:

- `nsid` (string, required): The id of the namespace in which the registry belongs.

- `crid` (string, optional): The id of the container registry to get. If not provided, all registry instances in the
  namespace will be returned.

Sample Request:

```bash
curl "https://osiriscloud.io/api/container-registry/default" -H "Authorization : Token <token>"
```

Sample Output:

```json
{
    "status": "success",
    "registries": [
        {
            "crid": "019415d1-9a35-7ae1-9515-21c7531eb412",
            "name": "Joe's Registry",
            "url": "registry.osiriscloud.io/joe",
            "public": false,
            "last_pushed_at": "2024-12-30T20:28:25.040Z",
            "created_at": "2024-12-30T04:27:25.621Z",
            "updated_at": "2024-12-30T20:41:19.210Z",
            "state": "active"
        }
    ],
    "message": "Get registry"
}
```

### Create Registry [/container-registry/{nsid}]

Method: `PUT`

Accepts: `application/json`

Returns: `application/json`

Parameters:

- `nsid` (string, required): The id of the namespace in which the registry belongs.

Request body parameters:

- `name` (string, required): Name of the container registry.
- `repo_name` (string, required): unique identifier for the container registry. This will be used to generate the URL.
- `public` (bool, optional): If `true`, the registry will allow pulling images without authentication. Default is `false`.

Sample Input:

```json
{
  "name": "CSAW",
  "repo_name": "csaw",
  "public": true
}
```

Sample Output:

```json
{
    "status": "success",
    "registry": {
        "crid": "01941953-2761-7273-8d6f-d4c63b2c7609",
        "name": "CSAW",
        "url": "registry.osiriscloud.io/csaw",
        "public": true,
        "last_pushed_at": null,
        "created_at": "2024-12-30T20:47:47.552Z",
        "updated_at": "2024-12-30T20:47:47.552Z",
        "state": "active"
    },
    "message": "Create registry"
}
```

### Update Registry [/container-registry/{nsid}/{crid}]

Method: `PATCH`

Accepts: `application/json`

Returns: `application/json`

Parameters:

- `nsid` (string, required): The id of the namespace in which the registry belongs.
- `crid` (string, optional): The id of the container registry.

Request body parameters:

- `name` (object, optional): Name of the container registry.
- `public` (string, optional): Password for the container registry.

Sample Input:

```json
{
  "name": "CSAW",
  "public": false
}
```

Sample Output:

```json
{
    "status": "success",
    "registry": {
        "crid": "01941953-2761-7273-8d6f-d4c63b2c7609",
        "name": "CSAW",
        "url": "registry.osiriscloud.io/csaw",
        "public": false,
        "last_pushed_at": null,
        "created_at": "2024-12-30T20:47:47.552Z",
        "updated_at": "2024-12-30T20:51:38.862Z",
        "state": "active"
    },
    "message": "Update registry"
}
```

### Delete Registry [/container-registry/{nsid}/{crid}]

Method: `DELETE`

Returns: `application/json`

Parameters:

- `nsid` (string, required): The id of the namespace in which the secret belongs.
- `crid` (string, required): Id of the container registry.

Sample Request:

```bash
curl -X DELETE "https://osiriscloud.io/api/container-registry/default/myapp2" -H "Authorization: Token <token>"
```

Sample Output:

```json
{
  "status": "success",
  "message": "Delete registry"
}
```

## Additional Functions

### Name check [/container-registry/name-check]

Method: `POST`

Returns: `application/json`

Request body parameters:

- `repo` (string, required): unique identifier for the container registry. This will be used to generate the URL.

Response body parameters:

- `available` (bool): If `true`, the slug is available.

### Stat [/container-registry/{nsid}/{crid}/stat]

Method: `POST`

Returns: `application/json`

Sample Output:

```json
{
    "status": "success",
    "stats": [
        {
            "sub": "alpine",
            "tags": [
                {
                    "name": "latest",
                    "size": 3645024,
                    "digest": "sha256:4048db5d36726e313ab8f7ffccf2362a34cba69e4cdd49119713483a68641fce"
                }
            ],
            "size": 3645024
        },
        {
            "sub": "nginx",
            "tags": [
                {
                    "name": "latest",
                    "size": 72937963,
                    "digest": "sha256:3b25b682ea82b2db3cc4fd48db818be788ee3f902ac7378090cf2624ec2442df"
                }
            ],
            "size": 72937963
        }
    ],
    "message": "Get registry stat"
}
```

### Delete Image [/container-registry/{nsid}/{crid}/delete]

Method: `POST`

Accepts: `application/json`

Returns: `application/json`

Request body parameters:

- `image` (string, required): Repository name for the container registry.
- `tag` (string, required): Tag name for the container registry.

Sample Output:

```json
{
  "status": "success",
  "message": "Delete registry image"
}
```
