# Keycloak Device Authorization Grant — Proof of Concept

Proves two things:

1. Different machine accounts can each complete the device flow.
2. Each machine's **offline** token is persisted in Keycloak's database.

## Keycloak Setup

In realm `machines`:

- **Shared confidential client** `machine-worker` with `offline_access` as an optional scope. All machines share this `client_id` / `client_secret`.
- **User Account per machine** manually created with a respective password

## Testing

`operator_flow.py`: Creates Grant code for operator to authenticate machine account
`offline_sessions`: does SQL query to show offline tokens found in the keycloak database

```bash
# 1. expose Keycloak (in another terminal)
kubectl port-forward svc/infra-keycloak 8080:8080

# 2. start the machine side
uv run operator_flow.py
```

Add the given code to localhost:8080/realms/machines/device and login with your user and password you set earlier
