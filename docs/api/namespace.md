## Namespaces

### Get Namespace(s) [/namespace/{nsid}]

Method: `GET`

Returns: `application/json`

Parameters

- `nsid` (str, optional): The id of the namespace to get. If not provided, all namespaces the user is part of will be
  returned. Using `default` as nsid will return the default namespace.

Sample Request:

`curl "https://osiriscloud.io/api/namespace/default" -H "Authorization : Token <token>"`

Sample Output:

```json
{
  "status": "success",
  "message": "Get namespace",
  "nsid": "fb123-ghn5",
  "name": "Default",
  "default": true,
  "created_at": "17:57:22, Wed 14 Aug 2024",
  "updated_at": "17:57:22, Wed 14 Aug 2024",
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

- `name` (str, required): The name of the namespace to create.
- `default` (bool, optional): Whether the namespace should be set as the default namespace. Defaults to false.
- `users` (list [dict], optional): A list of usernames with their role to add to the namespace. Defaults to an empty
  list.

Available roles are `manager` and `viewer`. `nsid` will be generated automatically and is immutable.

Sample Input:

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

Sample Output:

```json
{
  "status": "success",
  "message": "Create namespace",
  "nsid": "my-namespace-a5jt",
  "name": "My Namespace",
  "default": false,
  "created_at": "18:26:15, Wed 14 Aug 2024",
  "updated_at": "18:26:15, Wed 14 Aug 2024",
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

### Update Namespace [/namespace]

Method: `PATCH`

Accepts: `application/json`

Returns: `application/json`

Request body parameters:

- `nsid` (str, required): The id of the namespace to update
- `name` (str, optional): The new name of the namespace
- `default` (bool, optional): Whether the namespace should be set as the default namespace
- `owner` (dict, optional): The username of the new owner of the namespace
- `users` (list [dict], optional): A list of usernames with their role in to the namespace

<u>Note this when transferring the ownership</u>:

If the requester is not added as a user to the namespace after changing `owner`, they will lose access to the namespace.
Only the owner of a namespace can set it as their default namespace. If the `owner` is specified, and `default` is set
to `true`, the request will fail as the new owner is not the same as the user making the request. If this is the
requester's default namespace, they would have to set another namespace as their default before transferring
ownership as the system expects every user to have a default namespace they own.

Sample Input:

```json
{
  "nsid": "my-namespace-a5jt",
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

Sample Output:

```json
{
  "status": "success",
  "message": "Update namespace",
  "nsid": "my-namespace-a5jt",
  "name": "My Namespace for Real",
  "default": false,
  "created_at": "18:26:15, Wed 14 Aug 2024",
  "updated_at": "19:10:17, Wed 14 Aug 2024",
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

### Delete Namespace [/namespace]

Method: `DELETE`

Returns: `application/json`

Sample Input:

```json
{
  "nsid": "my-namespace-a5jt"
}
```

Sample Output:

```json
{
  "status": "success",
  "message": "Delete namespace",
  "nsid": "my-namespace-a5jt"
}
```
