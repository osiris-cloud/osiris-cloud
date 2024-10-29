## Secret Store

### Get Secrets [/secret-store/{nsid}/{secretid}]

Method: `GET`

Returns: `application/json`

Parameters:

- `nsid` (string, required): The id of the namespace in which the secret belongs.

- `secretid` (string, optional): The id of the secret to get. If not provided, all secrets in the namespace will be
  returned.

GET parameters:

- `type` (string, optional): The type of the secret to get. If not provided, all secrets in the namespace will be
  returned. Possible values are `opaque` and `auth`.


Sample Request:

```bash
curl "https://osiriscloud.io/api/secret-store/default" -H "Authorization : Token <token>"
```

Sample Response:

```json
{
  "status": "success",
  "message": "Get secret",
  "secrets": [
    {
      "secretid": "0192d47c-264c-7f11-980a-018916d83ed0",
      "name": "My App 1",
      "type": "opaque",
      "created_at": "2024-10-28T18:05:38.496Z",
      "updated_at": "2024-10-28T18:05:38.496Z",
      "state": "active"
    },
    {
      "secretid": "0192d47c-4ef6-75f2-82a6-b5a697525509",
      "name": "My App 2",
      "type": "opaque",
      "created_at": "2024-10-28T18:05:58.799Z",
      "updated_at": "2024-10-28T18:05:58.799Z",
      "state": "active"
    }
  ]
}
```

### Create Secret [/secret-store/{nsid}]

Method: `PUT`

Accepts: `application/json`

Returns: `application/json`

Parameters:

- `nsid` (string, required): The id of the namespace in which the secret belongs.

Request body parameters:

- `name` (string, required): Name of the secret.
- `type` (string, required): Osiris Cloud supports two types of secrets:
    - `opaque`: Secret composed of key-value pairs.
    - `auth`: Secret for authentication. Contains `username`, `password` , and/or `token` fields only. This type of
      secret is used for registry authentication.
- `values` (object, required): Each secret as key-value pairs. keys and values should be strings.

Sample Request:

```json
{
  "name": "Oauth Config",
  "type": "opaque",
  "values": {
    "CLIENT_ID": "231432487692",
    "CLIENT_SECRET": "fvbrk3vrer@e43v43rkv"
  }
}
```

Sample Response:

```json
{
  "status": "success",
  "message": "Create secret",
  "secretid": "0192d4d4-cebe-7aa1-8785-d20d6d9f026b",
  "state": "creating"
}
```

### Update Secret [/secret-store/{nsid}/{secretid}]

Method: `PATCH`

Accepts: `application/json`

Returns: `application/json`

Parameters:

- `nsid` (string, required): The id of the namespace in which the secret belongs.
- `secretid` (string, required): The id of the secret.

Request body parameters:

- `values` (object, required): Each secret as key-value pairs.

Sample Request:

```json
{
  "values": {
    "CLIENT_ID": "231432432",
    "CLIENT_SECRET": "updated123"
  }
}
```

Sample Response:

```json
{
  "status": "success",
  "message": "Update secret"
}
```

### Delete Secret [/secret-store/{nsid}/{secretid}]

Method: `DELETE`

Returns: `application/json`

Parameters:

- `nsid` (string, required): The id of the namespace in which the secret belongs.
- `secretid` (string, required): Unique id of the secret.


Sample Response:

```json
{
  "status": "success",
  "message": "Delete secret"
}
```

## Additional Functions

### Get Values [/secret-store/{nsid}/{secretid}/values]

Method: `POST`

Returns: `application/json`

Sample Response:

```json
{
  "status": "success",
  "values": {
    "PROD": "true",
    "API_KEY": "dingdongbingbongbangbangpfchangs4f"
  }
}
```
