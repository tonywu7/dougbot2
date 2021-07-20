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
  name: Scalars['String'];
  commands?: Maybe<Array<Maybe<Scalars['String']>>>;
  channels?: Maybe<Array<Maybe<Scalars['String']>>>;
  roles?: Maybe<Array<Maybe<Scalars['String']>>>;
  modifier: AclRoleModifier;
  action: AclAction;
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
  key: Scalars['String'];
  channel: Scalars['String'];
  role: Scalars['String'];
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
  itemId: Scalars['ID'];
  prefix: Scalars['String'];
};


export type MutationUpdateExtensionsArgs = {
  extensions: Array<Maybe<Scalars['String']>>;
  itemId: Scalars['ID'];
};


export type MutationUpdateModelsArgs = {
  itemId: Scalars['ID'];
};


export type MutationUpdateLoggingArgs = {
  config?: Maybe<Array<Maybe<LoggingEntryInput>>>;
  itemId: Scalars['ID'];
};


export type MutationDeleteAclArgs = {
  itemId: Scalars['ID'];
  names?: Maybe<Array<Maybe<Scalars['String']>>>;
};


export type MutationUpdateAclArgs = {
  changes?: Maybe<Array<Maybe<AccessControlInput>>>;
  itemId: Scalars['ID'];
};

export type Query = {
  __typename?: 'Query';
  bot?: Maybe<BotType>;
  server?: Maybe<ServerType>;
  logging?: Maybe<Array<Maybe<LoggingEntryType>>>;
  acl?: Maybe<Array<Maybe<AccessControlType>>>;
};


export type QueryServerArgs = {
  itemId: Scalars['ID'];
};


export type QueryLoggingArgs = {
  itemId: Scalars['ID'];
};


export type QueryAclArgs = {
  itemId: Scalars['ID'];
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

export type UpdateExtensionsMutationVariables = Exact<{
  itemId: Scalars['ID'];
  extensions: Array<Maybe<Scalars['String']>> | Maybe<Scalars['String']>;
}>;


export type UpdateExtensionsMutation = (
  { __typename?: 'Mutation' }
  & { updateExtensions?: Maybe<(
    { __typename?: 'ServerExtensionsMutation' }
    & { server?: Maybe<(
      { __typename?: 'ServerType' }
      & Pick<ServerType, 'extensions'>
    )> }
  )> }
);

export type UpdateModelsMutationVariables = Exact<{
  itemId: Scalars['ID'];
}>;


export type UpdateModelsMutation = (
  { __typename?: 'Mutation' }
  & { updateModels?: Maybe<(
    { __typename?: 'ServerModelSyncMutation' }
    & { server?: Maybe<(
      { __typename?: 'ServerType' }
      & Pick<ServerType, 'snowflake'>
    )> }
  )> }
);

export type UpdatePrefixMutationVariables = Exact<{
  itemId: Scalars['ID'];
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

export type BotDetailsQueryVariables = Exact<{ [key: string]: never; }>;


export type BotDetailsQuery = (
  { __typename?: 'Query' }
  & { bot?: Maybe<(
    { __typename?: 'BotType' }
    & Pick<BotType, 'commands'>
  )> }
);

export type ServerAclQueryVariables = Exact<{
  itemId: Scalars['ID'];
}>;


export type ServerAclQuery = (
  { __typename?: 'Query' }
  & { acl?: Maybe<Array<Maybe<(
    { __typename?: 'AccessControlType' }
    & Pick<AccessControlType, 'name' | 'commands' | 'channels' | 'roles' | 'modifier' | 'action' | 'error'>
  )>>> }
);

export type ServerDetailsQueryVariables = Exact<{
  itemId: Scalars['ID'];
}>;


export type ServerDetailsQuery = (
  { __typename?: 'Query' }
  & { server?: Maybe<(
    { __typename?: 'ServerType' }
    & Pick<ServerType, 'snowflake' | 'name' | 'prefix' | 'disabled' | 'extensions'>
    & { channels: Array<(
      { __typename?: 'ChannelType' }
      & Pick<ChannelType, 'snowflake' | 'name' | 'type' | 'order'>
    )>, roles: Array<(
      { __typename?: 'RoleType' }
      & Pick<RoleType, 'snowflake' | 'name' | 'color' | 'order' | 'perms'>
    )> }
  )> }
);
