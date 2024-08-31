## Secrets

### Get Secrets [/secret/{nsid}/{secret_name}]

Method: `GET`

Returns: `application/json`

Parameters:

- `nsid` (string, required): The id of the namespace in which the secret belongs.

- `secret_name` (string, optional): The name of the secret to get. If not provided, all secrets in the namespace will be
  returned.

Sample Request:

```bash
curl "https://osiriscloud.io/api/secret/default" -H "Authorization : Token <token>"
```

Sample Output:

```json
{
  "status": "success",
  "message": "Get secret",
  "secrets": [
    {
      "nsid": "fb123-ghn5",
      "name": "powerdns",
      "created_at": "19:47:02, Wed 14 Aug 2024",
      "updated_at": "19:47:02, Wed 14 Aug 2024",
      "values": {
        "PROD": "true",
        "API_KEY": "dingdongbingbongbangbangpfchangs4f"
      }
    },
    {
      "nsid": "fb123-ghn5",
      "name": "myapp",
      "created_at": "19:48:12, Wed 14 Aug 2024",
      "updated_at": "19:48:12, Wed 14 Aug 2024",
      "values": {
        "MY_KEY": "MY_VALUE"
      }
    }
  ]
}
```

### Create Secret [/secret/{nsid}]

Method: `POST`

Accepts: `application/json`

Returns: `application/json`

Parameters:

- `nsid` (string, required): The id of the namespace in which the secret belongs.

Request body parameters:

- `name` (string, required): Unique name of the secret.
- `values` (object, required): Each secret as key-value pairs.

Sample Input:

```json
{
  "name": "myapp2",
  "values": {
    "CLIENT_ID": "231432432",
    "CLIENT_SECRET": "fvbrk3vrer@(e43v43rkv"
  }
}
```

Sample Output:

```json
{
  "status": "success",
  "message": "Create secret",
  "nsid": "fb123-ghn5",
  "name": "myapp2",
  "values": {
    "CLIENT_ID": "231432432",
    "CLIENT_SECRET": "fvbrk3vrer@(e43v43rkv"
  }
}
```

### Update Secret [/secret/{nsid}/{secret_name}]

Method: `PATCH`

Accepts: `application/json`

Returns: `application/json`

Parameters:

- `nsid` (string, required): The id of the namespace in which the secret belongs.
- `secret_name` (string, required): Unique name of the secret.

Request body parameters:

- `values` (object, required): Each secret as key-value pairs.

Sample Input:

```json
{
  "values": {
    "CLIENT_ID": "231432432",
    "CLIENT_SECRET": "updated123"
  }
}
```

Sample Output:

```json
{
  "status": "success",
  "message": "Update secret",
  "nsid": "fb123-ghn5",
  "name": "myapp2",
  "values": {
    "CLIENT_ID": "231432432",
    "CLIENT_SECRET": "updated123"
  }
}
```

### Delete Secret [/secret/{nsid}/{secret_name}]

Method: `DELETE`

Returns: `application/json`

Parameters:

- `nsid` (string, required): The id of the namespace in which the secret belongs.
- `secret_name` (string, required): Unique name of the secret.

Sample Request:

```bash
curl -X DELETE "https://osiriscloud.io/api/secret/fb123-ghn5/myapp2" -H "Authorization: Token <token>"
```

Sample Output:

```json
{
  "status": "success",
  "message": "Delete secret",
  "name": "myapp2"
}
```
