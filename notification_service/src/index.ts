import { env } from './config/env';
import { createServer } from './server';

function main() {
  const { httpServer } = createServer();

  httpServer.listen(env.PORT, () => {
    console.log(`notification_service listening on port ${env.PORT} [${env.NODE_ENV}]`);
  });
}

main();