import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    // The suite exercises the real Prisma client against the dev database, so it
    // needs the same env (DATABASE_URL, secrets) the service reads at import. A
    // single fork keeps those connections from being opened once per file.
    pool: 'forks',
    maxWorkers: 1,
    include: ['tests/**/*.test.ts'],
    testTimeout: 20_000,
    hookTimeout: 20_000,
    // Counts are asserted absolutely, so the files must not interleave.
    sequence: { concurrent: false },
  },
});
