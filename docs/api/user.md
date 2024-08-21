## Users

### Get user [/user/{username}]

Method: `GET`

Returns: `application/json`

Parameters

- `username` (string, optional): The username of the user to get. The requester can use this to get their own info.
  Cluster admins can use this to get any user's information. Not providing a username will get all users.

Sample Request:

```bash
curl "https://osiriscloud.io/api/user/fb123" -H "Authorization: Token <token>"
```

Sample Output:

```json
{
  "status": "success",
  "message": "Get user",
  "username": "fb123",
  "first_name": "Foo",
  "last_name": "Bar",
  "email": "fb123@nyu.edu",
  "avatar": "https://blob.osiriscloud.io/profile.webp",
  "date_joined": "16:40:22, Wed 14 Aug 2024",
  "last_login": "17:51:28, Wed 14 Aug 2024",
  "default_nsid": "fb123-ghn5",
  "cluster_role": "user",
  "github": null,
  "namespaces": [
    "fb123-ghn5",
    "my-namespace-a5jt"
  ],
  "resource_used": {
    "cpu": 2,
    "ram": 4,
    "disk": 30,
    "public_ip": 0,
    "gpu": 0
  },
  "resource_limit": {
    "cpu": 24,
    "ram": 32,
    "disk": 512,
    "public_ip": 5,
    "gpu": 5
  }
}
```

### Create user [/user]

Method: `POST`

Currently relies on OIDC/SAML JIT provisioning. Default limits are assigned when created. Will implement later.

### Update User [/user/{username}]

Method: `PATCH`

Accepts: `application/json`

Returns: `application/json`

Request body parameters:

+ `first_name` (string, optional): New first name.
+ `last_name` (string, optional): New last name.
+ `email` (string, optional): New email of the user.
+ `avatar` (string, optional): Valid image url. Supports JPEG, PNG, and GIF. Max file size is 5 MB.
+ `default_nsid` (string, optional): `nsid` of the default namespace. The user is assumed to be the owner of the new
  namespace.
+ `cluster_role` (string, optional): Cluster role of the user. This can be set only by a cluster admin. Available roles
  are:
    + `super_admin`: Has full control of the cluster and can view, edit or delete any resource.
    + `admin`: Has some administrative privileges including being able to view, edit and allocate resources for
      namespace and user groups. Groups will be implemented in the future.
    + `user`: Default role for a newly joined user (unless changed). They can manage resources they create. Default
      limits are applied, when the account is provisioned.
    + `guest`: Can log in but limits are set to 0, ie they cannot create new resources but can interact with resources
      shared with them. If an existing user is downgraded to guest or below, the cluster role downgrade action is
      applied.
    + `blocked`: No access.
+ `resource_limit` (object, optional): This limits what the user can create. Setting value to `null` means no limit
  will be imposed. Values that can be set are:
    + `cpu` (integer, optional): The number of vCPU's.
    + `ram` (integer, optional): Total system memory in GB.
    + `disk` (integer, optional): Total storage in GiB.
    + `public_ip` (integer, optional): Public IPs, if enabled.
    + `gpu` (integer, optional): vGPUs, if enabled.

<u>Note</u>:
Even though the api allows admins to view and edit resources, this does not give direct access to the resource and
user resource data.

Sample Input:

```json
{
  "first_name": "Fu",
  "resource_limit": {
    "cpu": null
  }
}
```

Sample Output:

```json
{
  "status": "success",
  "message": "Update user",
  "username": "fb123",
  "first_name": "Fu",
  "last_name": "Bar",
  "email": "fb123@nyu.edu",
  "avatar": "https://blob.osiriscloud.io/profile.webp",
  "date_joined": "16:40:22, Wed 14 Aug 2024",
  "last_login": "17:51:28, Wed 14 Aug 2024",
  "default_nsid": "fb123-ghn5",
  "cluster_role": "user",
  "github": null,
  "namespaces": [
    "fb123-ghn5",
    "my-namespace-a5jt"
  ],
  "resource_used": {
    "cpu": 2,
    "ram": 4,
    "disk": 30,
    "public_ip": 0,
    "gpu": 0
  },
  "resource_limit": {
    "cpu": null,
    "ram": 32,
    "disk": 512,
    "public_ip": 5,
    "gpu": 5
  }
}
```

### Delete User [/user/{username}]

Method: `DELETE`

Returns: `application/json`

Parameters

- `username` (string, required): The username of the user to delete. Only a cluster admin is permitted to do this.
  All resources owned by the user will be deleted.

Sample Request:

```bash
curl -X DELETE "https://osiriscloud.io/api/user/bb789" -H "Authorization: Token <token>"
```

Sample Output:

```bash
{
  "status": "success",
  "message": "Delete user",
  "username": "bb789"
}
```
