
declare module '*/server-info.graphql' {
  import { DocumentNode } from 'graphql';
  const defaultDocument: DocumentNode;
  export const serverInfo: DocumentNode;

  export default defaultDocument;
}
    