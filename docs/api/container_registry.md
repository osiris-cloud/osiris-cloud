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
  "message": "Get container registry",
  "nsid": "fb123-ghn5",
  "registries": [
    {
      "name": "CSAW Prod",
      "crid": "b4342907-4bbc-4c92-b675-30d86bf6791e",
      "created_at": "19:47:02, Thu 15 Aug 2024",
      "updated_at": "19:47:02, Thu 15 Aug 2024",
      "url": "csaw.registry.osiriscloud.io",
      "state": "active"
    },
    {
      "name": "CSAW Test",
      "crid": "92680506-381a-4958-9f2e-a441b9379437",
      "created_at": "19:17:09, Thu 15 Aug 2024",
      "updated_at": "19:17:09, Thu 15 Aug 2024",
      "url": "csaw-test.registry.osiriscloud.io",
      "state": "active"
    }
  ]
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
- `slug` (string, required): unique identifier for the container registry. This will be used to generate the URL.
- `password` (string, required): Password for the container registry.

Sample Input:

```json
{
  "name": "CSAW Prod",
  "slug": "csaw",
  "password": "password"
}
```

Sample Output:

```json
{
  "status": "success",
  "name": "CSAW Test",
  "crid": "92680506-381a-4958-9f2e-a441b9379437",
  "created_at": "19:17:09, Thu 15 Aug 2024",
  "updated_at": "19:17:09, Thu 15 Aug 2024",
  "url": "csaw-test.registry.osiriscloud.io",
  "state": "creating"
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
- `password` (string, optional): Password for the container registry.

Sample Input:

```json
{
  "name": "CSAW",
  "password": "password"
}
```

Sample Output:

```json
{
  "status": "success",
  "name": "CSAW Test",
  "crid": "92680506-381a-4958-9f2e-a441b9379437",
  "created_at": "19:17:09, Thu 15 Aug 2024",
  "updated_at": "19:20:05, Thu 15 Aug 2024",
  "url": "csaw-test.registry.osiriscloud.io",
  "state": "active"
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
  "message": "Delete container registry",
  "crid": "92680506-381a-4958-9f2e-a441b9379437"
}
```

## Additional Functions

### Name check [/container-registry/name-check]

Method: `POST`

Returns: `application/json`

Request body parameters:

- `slug` (string, required): unique identifier for the container registry. This will be used to generate the URL.

Response body parameters:

- `available` (bool, required): If `true`, the slug is available.

### Stat [/container-registry/{nsid}/{crid}/stat]

Method: `POST`

Returns: `application/json`

Sample Output:

```json
{
  "status": "success",
  "stats": [
    {
      "repo": "ubuntu",
      "tags": [
        {
          "name": "latest",
          "size": 30613777,
          "digest": "sha256:61b2756d6fa9d6242fafd5b29f674404779be561db2d0bd932aa3640ae67b9e1"
        }
      ],
      "size": 30613777
    }
  ],
  "message": "Get registry stat"
}
```

### Get Credentials [/container-registry/{nsid}/{crid}/creds]

Method: `POST`

Returns: `application/json`

Sample Output:

```json
{
  "status": "success",
  "creds": {
    "username": "osiris",
    "password": "b4ozaBZeLbf1G8l1QYTKf1oEEvm68b7w"
  },
  "message": "Get login"
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
