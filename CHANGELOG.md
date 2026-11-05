# Changelog

## Unreleased

- Started the full dashboard information-architecture redesign: dedicated agent detail pages, provider and platform directories, and direct Operations subpages. Existing Flask APIs and runtime data remain the source of truth.

- Introduced a shared dashboard theme inspired by msf-web-console: compact dark surfaces, restrained green accents, consistent controls, and responsive navigation.

- Standardized the product on a single browser-accessed web application.
- Introduced the src-layout Python package and a single server entrypoint.
- Removed desktop-window wrappers and executable-build workflows from the target product.
- Preserved existing runtime data locations during the initial code migration.
