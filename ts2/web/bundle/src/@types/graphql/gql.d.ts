
declare module '*/serverPrefix.graphql' {
  import { DocumentNode } from 'graphql';
  const defaultDocument: DocumentNode;
  export const serverPrefix: DocumentNode;

  export default defaultDocument;
}
    