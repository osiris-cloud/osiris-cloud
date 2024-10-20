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
      "public": false
    },
    {
      "name": "CSAW Test",
      "crid": "92680506-381a-4958-9f2e-a441b9379437",
      "created_at": "19:17:09, Thu 15 Aug 2024",
      "updated_at": "19:17:09, Thu 15 Aug 2024",
      "url": "csaw-test.registry.osiriscloud.io",
      "public": false
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
- `public` (bool, optional): If true, the registry will be public. In public mode, users can pull without
  authentication. Default is false.

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
  "public": false
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

- `name` (object, required): Each secret as key-value pairs.
- `public` (bool, optional): If true, the registry will be public. In public mode, users can pull without
  authentication. Default is false.

Sample Input:

```json
{
  "name": "CSAW Test",
  "public": true
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
  "public": true
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

Accepts: `application/json`

Returns: `application/json`

Request body parameters:

- `slug` (string, required): unique identifier for the container registry. This will be used to generate the URL.

Response body parameters:
- `available` (bool, required): If true, the slug is available. If false, the slug is already taken.

