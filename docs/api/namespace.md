## Namespaces

### Get Namespace(s) [/namespace/{nsid}]

Method: `GET`

Returns: `application/json`

Parameters

- `nsid` (string, optional): The id of the namespace to get. If not provided, all namespaces the user is part of will be
  returned. Using `default` as nsid will return the default namespace.

Sample Request:

```bash
curl "https://osiriscloud.io/api/namespace/default" -H "Authorization : Token <token>"
```

Sample Response:

```json
{
  "status": "success",
  "message": "Get namespace",
  "nsid": "fb123-ghn5",
  "name": "Default",
  "default": true,
  "created_at": "2024-10-20T18:26:11.556Z",
  "updated_at": "2024-10-20T18:26:11.556Z",
  "owner": {
    "username": "fb123",
    "name": "Foo Bar",
    "email": "fb123@nyu.edu",
    "avatar": "https://blob.osiriscloud.io/profile.webp"
  },
  "users": []
}
```

### Create Namespace [/namespace]

Method: `POST`

Accepts: `application/json`

Returns: `application/json`

Request body parameters:

- `name` (string, required): The name of the namespace to create.
- `default` (bool, optional): Whether the namespace should be set as the default namespace. Defaults to false.
- `users` (array [object], optional): A list of usernames with their role to add to the namespace. Defaults to an empty
  list.

Available roles are `manager` and `viewer`. `nsid` will be generated automatically and is immutable.

Sample Request:

```json
{
  "name": "My Namespace",
  "default": false,
  "users": [
    {
      "username": "aa456",
      "role": "manager"
    },
    {
      "username": "bb789",
      "role": "viewer"
    }
  ]
}
```

Sample Response:

```json
{
  "status": "success",
  "message": "Create namespace",
  "nsid": "my-namespace-a5jt",
  "name": "My Namespace",
  "default": false,
  "created_at": "2024-10-20T18:26:11.556Z",
  "updated_at": "2024-10-20T18:26:11.556Z",
  "owner": {
    "username": "fb123",
    "name": "Foo Bar",
    "email": "fb123@nyu.edu",
    "avatar": "https://blob.osiriscloud.io/profile.webp"
  },
  "users": [
    {
      "username": "aa456",
      "name": "Alice Algorithm",
      "email": "aa456@nyu.edu",
      "role": "manager",
      "avatar": "https://blob.osiriscloud.io/profile.webp"
    },
    {
      "username": "bb789",
      "name": "Bob Binary",
      "email": "bb789@nyu.edu",
      "role": "viewer",
      "avatar": "https://blob.osiriscloud.io/profile.webp"
    }
  ]
}
```

### Update Namespace [/namespace/{nsid}]

Method: `PATCH`

Accepts: `application/json`

Returns: `application/json`

Request body parameters:

- `name` (string, optional): The new name of the namespace.
- `default` (bool, optional): Whether the namespace should be set as the default namespace.
- `owner` (object, optional): The username of the new owner of the namespace.
- `users` (array [object], optional): A list of usernames with their role in to the namespace.

<u>Note this when transferring the ownership</u>:

If the requester is not added as a user to the namespace after changing `owner`, they will lose access to the namespace.
Only the owner of a namespace can set it as their default namespace. If the `owner` is specified, and `default` is set
to `true`, the request will fail as the new owner is not the same as the user making the request. If this is the
requester's default namespace, they would have to set another namespace as their default before transferring
ownership as the system expects every user to have a default namespace they own.

Sample Request:

```json
{
  "name": "My Namespace for Real",
  "default": false,
  "owner": {
    "username": "aa456"
  },
  "users": [
    {
      "username": "bb789",
      "role": "viewer"
    },
    {
      "username": "fb123",
      "role": "manager"
    }
  ]
}
```

Sample Response:

```json
{
  "status": "success",
  "message": "Update namespace",
  "nsid": "my-namespace-a5jt",
  "name": "My Namespace for Real",
  "default": false,
  "created_at": "2024-10-20T18:26:11.556Z",
  "updated_at": "2024-10-20T18:26:11.556Z",
  "owner": {
    "username": "aa456",
    "name": "Alice Algorithm",
    "email": "aa456@nyu.edu",
    "avatar": "https://blob.osiriscloud.io/profile.webp"
  },
  "users": [
    {
      "username": "fb123",
      "name": "Foo Bar",
      "email": "fb123@nyu.edu",
      "role": "manager",
      "avatar": "https://blob.osiriscloud.io/profile.webp"
    },
    {
      "username": "bb789",
      "name": "Bob Binary",
      "email": "bb789@nyu.edu",
      "role": "viewer",
      "avatar": "https://blob.osiriscloud.io/profile.webp"
    }
  ]
}
```

### Delete Namespace [/namespace/{nsid}]

Method: `DELETE`

Returns: `application/json`

Sample Request:

```bash
curl -X DELETE "https://osiriscloud.io/api/namespace/my-namespace-a5jt" -H "Authorization: Token <token>"
```

Sample Response:

```json
{
  "status": "success",
  "message": "Delete namespace",
  "nsid": "my-namespace-a5jt"
}
```
