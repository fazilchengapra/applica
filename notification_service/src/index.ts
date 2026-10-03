import { env } from './config/env';
import { prisma } from './lib/prisma';
import { createServer } from './server';

function main() {
  const { httpServer, webSocketServer, pubClient, subClient, eventSubscriber } = createServer();

  httpServer.listen(env.PORT, () => {
    console.log(`notification_service listening on port ${env.PORT} [${env.NODE_ENV}]`);
  });

  process.on('SIGTERM', async () => {
    console.log('shutting_down');
    webSocketServer.close();
    await eventSubscriber.quit();
    await pubClient.quit();
    await subClient.quit();
    // Release the Postgres pool before the process exits, so an in-flight
    // request is not cut off mid-statement and the server does not wait on
    // keepalive timeouts to let go of the connections.
    await prisma.$disconnect();
    httpServer.close(() => process.exit(0));
  });
}

main();