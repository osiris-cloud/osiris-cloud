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
  returned. Possible values are `opaque` and `dockerconfig`.

Sample Request:

```bash
curl "https://osiriscloud.io/api/secret-store/default" -H "Authorization : Token <token>"
```

Sample Response:

```json
{
  "status": "success",
  "secrets": [
    {
      "secretid": "01942f7d-8c9b-7a30-8b0a-48ae2b1c4533",
      "name": "My secret",
      "type": "opaque",
      "created_at": "2025-01-04T04:05:44.731Z",
      "updated_at": "2025-01-04T04:07:44.756Z"
    },
    {
      "secretid": "01942f80-c2bd-7f41-acb5-cc5c1c49e57d",
      "name": "ECR Pull Secret",
      "type": "dockerconfig",
      "created_at": "2025-01-04T04:09:15.196Z",
      "updated_at": "2025-01-04T04:09:15.207Z"
    }
  ],
  "message": "Get secrets"
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
    - `dockerconfig`: This type of secret is used for external registry authentication.
- `values` (object, optional): Each secret as key-value pairs. keys and values should be strings. You may also create a
  secret with an empty object.

Sample Request:

```json
{
  "name": "My secret",
  "type": "opaque",
  "values": {
    "PROD": "True",
    "API_KEY": "dingdongbingbongbangbangpfchangs"
  }
}
```

Sample Response:

```json
{
  "status": "success",
  "secret": {
    "secretid": "01942f7d-8c9b-7a30-8b0a-48ae2b1c4533",
    "name": "My secret",
    "type": "opaque",
    "created_at": "2025-01-04T04:05:44.731Z",
    "updated_at": "2025-01-04T04:05:44.739Z"
  },
  "message": "Create Secret"
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

- `name` (string, optional): Name of the secret.
- `values` (object, optional): Each secret as key-value pairs.

Sample Request:

```json
{
  "values": {
    "PROD": "False",
    "API_KEY": "dingdongbingbongbangbangpfchangs"
  }
}
```

Sample Response:

```json
{
  "status": "success",
  "secret": {
    "secretid": "01942f7d-8c9b-7a30-8b0a-48ae2b1c4533",
    "name": "My secret",
    "type": "opaque",
    "created_at": "2025-01-04T04:05:44.731Z",
    "updated_at": "2025-01-04T04:07:44.756Z"
  },
  "message": "Update Secret"
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
    "PROD": "True",
    "API_KEY": "dingdongbingbongbangbangpfchangs"
  }
}
```
