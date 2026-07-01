import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'node',
    include: ['tests/**/*.test.ts'],
    globals: false,
    clearMocks: true,
    restoreMocks: true,
    // Real PNG (sharp) and PDF (pdf-lib) rendering, plus first-time worker/native
    // init, can momentarily exceed the 5s default when the machine is under heavy
    // load. A generous timeout keeps the suite reliable in CI without masking the
    // sub-second happy path. (Render/callback *behaviour* timeouts are tested
    // explicitly via withTimeout / the callback client, not via this value.)
    testTimeout: 30_000,
    hookTimeout: 30_000,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      reportsDirectory: './coverage',
      include: ['src/**/*.ts'],
      exclude: [
        // Process entrypoint: calls listen()/process.exit and is never imported
        // by tests — exercised only via the built app (src/app.ts), which is
        // covered directly.
        'src/server.ts',
        // Pure type-only modules (interfaces/type aliases), no executable code.
        'src/jobs/job.types.ts',
        'src/renderers/renderer.types.ts',
        'src/storage/storage.types.ts',
      ],
      thresholds: {
        lines: 70,
        functions: 65,
        branches: 55,
        statements: 70,
      },
    },
  },
});
