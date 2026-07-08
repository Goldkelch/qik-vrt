# QIK-VRT GitHub App Target Blueprint

4AU still uses owner-provided installation tokens for bootstrapping. Product operation should move to a GitHub App with repository-scoped installation, least privilege, and short-lived installation tokens.

Required target permissions:

- Contents: read/write
- Actions: read/write or workflow dispatch capability
- Metadata: read

The app must not write to foreign repositories. Each installed repository writes only to itself.
