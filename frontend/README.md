# Frontend

## Setup

1.  Install dependencies:
    ```bash
    pnpm install
    ```

2.  Run development server:
    ```bash
    pnpm dev
    ```

## Recent Changes

-   Fixed `radix-ui` imports in `components/ui/*.tsx` to use specific `@radix-ui/react-*` packages.
-   Replaced missing `classnames` dependency with `cn` utility in `components/toolbar.tsx` and `components/weather.tsx`.
-   Added missing `use-mobile` hook in `hooks/use-mobile.ts`.
-   Ensured proper `next`, `react`, and `ai` dependencies are configured.

## Troubleshooting

If you encounter module not found errors, ensure you have run `pnpm install` and that `pnpm-lock.yaml` is up to date.
