# General implementation skill

Apply these rules when generating any implementation package:

- optimize for measurable business value,
- prefer the simplest architecture that can be audited,
- separate read-only steps from write actions,
- require explicit approval before any production mutation,
- document data sources, permissions, failure modes, and rollback steps,
- state assumptions when information is missing,
- and avoid vendor lock-in unless the client has already standardized on a platform.
