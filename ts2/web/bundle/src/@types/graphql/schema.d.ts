export type Maybe<T> = T | null;
export type Exact<T extends { [key: string]: unknown }> = { [K in keyof T]: T[K] };
export type MakeOptional<T, K extends keyof T> = Omit<T, K> & { [SubKey in K]?: Maybe<T[SubKey]> };
export type MakeMaybe<T, K extends keyof T> = Omit<T, K> & { [SubKey in K]: Maybe<T[SubKey]> };
/** All built-in and custom scalars, mapped to their actual values */
export type Scalars = {
  ID: string;
  String: string;
  Boolean: boolean;
  Int: number;
  Float: number;
};

/** An enumeration. */
export enum AclAction {
  Enabled = 'ENABLED',
  Disabled = 'DISABLED'
}

export type AclDeleteMutation = {
  __typename?: 'ACLDeleteMutation';
  success?: Maybe<Scalars['Boolean']>;
};

/** An enumeration. */
export enum AclRoleModifier {
  None = 'NONE',
  Any = 'ANY',
  All = 'ALL'
}

export type AclUpdateMutation = {
  __typename?: 'ACLUpdateMutation';
  acl?: Maybe<Array<Maybe<AccessControlType>>>;
};

export type AccessControlInput = {
  name?: Maybe<Scalars['String']>;
  commands?: Maybe<Array<Maybe<Scalars['String']>>>;
  channels?: Maybe<Array<Maybe<Scalars['String']>>>;
  roles?: Maybe<Array<Maybe<Scalars['String']>>>;
  modifier?: Maybe<AclRoleModifier>;
  action?: Maybe<AclAction>;
  error?: Maybe<Scalars['String']>;
};

export type AccessControlType = {
  __typename?: 'AccessControlType';
  name?: Maybe<Scalars['String']>;
  commands?: Maybe<Array<Maybe<Scalars['String']>>>;
  channels?: Maybe<Array<Maybe<Scalars['String']>>>;
  roles?: Maybe<Array<Maybe<Scalars['String']>>>;
  modifier?: Maybe<AclRoleModifier>;
  action?: Maybe<AclAction>;
  specificity?: Maybe<Array<Maybe<Scalars['Int']>>>;
  error?: Maybe<Scalars['String']>;
};

export type BotType = {
  __typename?: 'BotType';
  commands?: Maybe<Array<Maybe<Scalars['String']>>>;
};

/** An enumeration. */
export enum ChannelEnum {
  Text = 'text',
  Private = 'private',
  Voice = 'voice',
  Group = 'group',
  Category = 'category',
  News = 'news',
  Store = 'store',
  StageVoice = 'stage_voice'
}

export type ChannelType = {
  __typename?: 'ChannelType';
  snowflake: Scalars['String'];
  name: Scalars['String'];
  guild: ServerType;
  order: Scalars['Int'];
  type?: Maybe<ChannelEnum>;
};

export type LoggingEntryInput = {
  key?: Maybe<Scalars['String']>;
  name?: Maybe<Scalars['String']>;
  channel?: Maybe<Scalars['String']>;
  role?: Maybe<Scalars['String']>;
};

export type LoggingEntryType = {
  __typename?: 'LoggingEntryType';
  key?: Maybe<Scalars['String']>;
  name?: Maybe<Scalars['String']>;
  channel?: Maybe<Scalars['String']>;
  role?: Maybe<Scalars['String']>;
};

export type LoggingMutation = {
  __typename?: 'LoggingMutation';
  logging?: Maybe<Array<Maybe<LoggingEntryType>>>;
};

export type Mutation = {
  __typename?: 'Mutation';
  updatePrefix?: Maybe<ServerPrefixMutation>;
  updateExtensions?: Maybe<ServerExtensionsMutation>;
  updateModels?: Maybe<ServerModelSyncMutation>;
  updateLogging?: Maybe<LoggingMutation>;
  deleteACL?: Maybe<AclDeleteMutation>;
  updateACL?: Maybe<AclUpdateMutation>;
};


export type MutationUpdatePrefixArgs = {
  id: Scalars['ID'];
  prefix: Scalars['String'];
};


export type MutationUpdateExtensionsArgs = {
  extensions: Array<Maybe<Scalars['String']>>;
  id: Scalars['ID'];
};


export type MutationUpdateModelsArgs = {
  id: Scalars['ID'];
};


export type MutationUpdateLoggingArgs = {
  config?: Maybe<Array<Maybe<LoggingEntryInput>>>;
  id: Scalars['ID'];
};


export type MutationDeleteAclArgs = {
  id: Scalars['ID'];
  name: Scalars['String'];
};


export type MutationUpdateAclArgs = {
  changes?: Maybe<Array<Maybe<AccessControlInput>>>;
  id: Scalars['ID'];
};

export type Query = {
  __typename?: 'Query';
  bot?: Maybe<BotType>;
  server?: Maybe<ServerType>;
  logging?: Maybe<Array<Maybe<LoggingEntryType>>>;
  acl?: Maybe<Array<Maybe<AccessControlType>>>;
};


export type QueryServerArgs = {
  id: Scalars['String'];
};


export type QueryLoggingArgs = {
  server: Scalars['String'];
};


export type QueryAclArgs = {
  server: Scalars['String'];
};

export type RoleType = {
  __typename?: 'RoleType';
  snowflake: Scalars['String'];
  name: Scalars['String'];
  color: Scalars['Int'];
  guild: ServerType;
  perms: Scalars['String'];
  order: Scalars['Int'];
};

export type ServerExtensionsMutation = {
  __typename?: 'ServerExtensionsMutation';
  server?: Maybe<ServerType>;
};

export type ServerModelSyncMutation = {
  __typename?: 'ServerModelSyncMutation';
  server?: Maybe<ServerType>;
};

export type ServerPrefixMutation = {
  __typename?: 'ServerPrefixMutation';
  server?: Maybe<ServerType>;
};

export type ServerType = {
  __typename?: 'ServerType';
  snowflake: Scalars['String'];
  disabled: Scalars['Boolean'];
  prefix: Scalars['String'];
  name: Scalars['String'];
  perms: Scalars['String'];
  channels: Array<ChannelType>;
  roles: Array<RoleType>;
  extensions?: Maybe<Array<Maybe<Scalars['String']>>>;
};

export type UpdatePrefixMutationVariables = Exact<{
  id: Scalars['ID'];
  prefix: Scalars['String'];
}>;


export type UpdatePrefixMutation = (
  { __typename?: 'Mutation' }
  & { updatePrefix?: Maybe<(
    { __typename?: 'ServerPrefixMutation' }
    & { server?: Maybe<(
      { __typename?: 'ServerType' }
      & Pick<ServerType, 'prefix'>
    )> }
  )> }
);

export type ServerInfoQueryVariables = Exact<{
  id: Scalars['String'];
}>;


export type ServerInfoQuery = (
  { __typename?: 'Query' }
  & { server?: Maybe<(
    { __typename?: 'ServerType' }
    & Pick<ServerType, 'snowflake' | 'name' | 'prefix'>
  )> }
);
