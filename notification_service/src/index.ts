import { env } from './config/env';
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
    httpServer.close(() => process.exit(0));
  });
}

main();