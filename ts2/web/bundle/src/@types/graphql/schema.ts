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
export enum ACLAction {
  ENABLED = 'ENABLED',
  DISABLED = 'DISABLED'
}

export type ACLDeleteMutation = {
  __typename?: 'ACLDeleteMutation';
  success?: Maybe<Scalars['Boolean']>;
};

/** An enumeration. */
export enum ACLRoleModifier {
  NONE = 'NONE',
  ANY = 'ANY',
  ALL = 'ALL'
}

export type ACLUpdateMutation = {
  __typename?: 'ACLUpdateMutation';
  acl?: Maybe<Array<Maybe<AccessControlType>>>;
};

export type AccessControlInput = {
  name: Scalars['String'];
  commands?: Maybe<Array<Maybe<Scalars['String']>>>;
  channels?: Maybe<Array<Maybe<Scalars['String']>>>;
  roles?: Maybe<Array<Maybe<Scalars['String']>>>;
  modifier: ACLRoleModifier;
  action: ACLAction;
  error?: Maybe<Scalars['String']>;
};

export type AccessControlType = {
  __typename?: 'AccessControlType';
  name: Scalars['String'];
  commands?: Maybe<Array<Scalars['String']>>;
  channels?: Maybe<Array<Scalars['String']>>;
  roles?: Maybe<Array<Scalars['String']>>;
  modifier: ACLRoleModifier;
  action: ACLAction;
  specificity?: Maybe<Array<Scalars['Int']>>;
  error?: Maybe<Scalars['String']>;
};

export type BotType = {
  __typename?: 'BotType';
  commands?: Maybe<Array<Maybe<Scalars['String']>>>;
};

/** An enumeration. */
export enum ChannelEnum {
  text = 'text',
  private = 'private',
  voice = 'voice',
  group = 'group',
  category = 'category',
  news = 'news',
  store = 'store',
  stage_voice = 'stage_voice'
}

export type ChannelType = {
  __typename?: 'ChannelType';
  snowflake: Scalars['String'];
  name: Scalars['String'];
  guild: ServerType;
  order: Scalars['Int'];
  category?: Maybe<ChannelType>;
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

export type LoggingUpdateMutation = {
  __typename?: 'LoggingUpdateMutation';
  logging?: Maybe<Array<Maybe<LoggingEntryType>>>;
};

export type Mutation = {
  __typename?: 'Mutation';
  updateTimezones?: Maybe<RoleTimezoneUpdateMutation>;
  deleteTimezones?: Maybe<RoleTimezoneDeleteMutation>;
  deleteACL?: Maybe<ACLDeleteMutation>;
  updateACL?: Maybe<ACLUpdateMutation>;
  updateLogging?: Maybe<LoggingUpdateMutation>;
  updatePrefix?: Maybe<ServerPrefixMutation>;
  updateExtensions?: Maybe<ServerExtensionsMutation>;
  updateModels?: Maybe<ServerModelSyncMutation>;
  updatePerms?: Maybe<ServerPermMutation>;
};


export type MutationupdateTimezonesArgs = {
  serverId: Scalars['ID'];
  timezones?: Maybe<Array<Maybe<RoleTimezoneInput>>>;
};


export type MutationdeleteTimezonesArgs = {
  roleIds?: Maybe<Array<Maybe<Scalars['String']>>>;
  serverId: Scalars['ID'];
};


export type MutationdeleteACLArgs = {
  names?: Maybe<Array<Maybe<Scalars['String']>>>;
  serverId: Scalars['ID'];
};


export type MutationupdateACLArgs = {
  changes?: Maybe<Array<Maybe<AccessControlInput>>>;
  serverId: Scalars['ID'];
};


export type MutationupdateLoggingArgs = {
  config?: Maybe<Array<Maybe<LoggingEntryInput>>>;
  serverId: Scalars['ID'];
};


export type MutationupdatePrefixArgs = {
  prefix: Scalars['String'];
  serverId: Scalars['ID'];
};


export type MutationupdateExtensionsArgs = {
  extensions: Array<Maybe<Scalars['String']>>;
  serverId: Scalars['ID'];
};


export type MutationupdateModelsArgs = {
  serverId: Scalars['ID'];
};


export type MutationupdatePermsArgs = {
  readable: Array<Maybe<Scalars['ID']>>;
  serverId: Scalars['ID'];
  writable: Array<Maybe<Scalars['ID']>>;
};

export type Query = {
  __typename?: 'Query';
  timezones?: Maybe<Array<Maybe<RoleTimezoneType>>>;
  templates?: Maybe<Array<Maybe<StringTemplateType>>>;
  acl?: Maybe<Array<Maybe<AccessControlType>>>;
  logging?: Maybe<Array<Maybe<LoggingEntryType>>>;
  bot?: Maybe<BotType>;
  server?: Maybe<ServerType>;
};


export type QuerytimezonesArgs = {
  serverId: Scalars['ID'];
};


export type QuerytemplatesArgs = {
  serverId: Scalars['ID'];
};


export type QueryaclArgs = {
  serverId: Scalars['ID'];
};


export type QueryloggingArgs = {
  serverId: Scalars['ID'];
};


export type QueryserverArgs = {
  serverId: Scalars['ID'];
};

export type RoleTimezoneDeleteMutation = {
  __typename?: 'RoleTimezoneDeleteMutation';
  success?: Maybe<Scalars['Boolean']>;
};

export type RoleTimezoneInput = {
  roleId: Scalars['ID'];
  timezone: Scalars['String'];
};

export type RoleTimezoneType = {
  __typename?: 'RoleTimezoneType';
  timezone: Scalars['String'];
  roleId: Scalars['ID'];
};

export type RoleTimezoneUpdateMutation = {
  __typename?: 'RoleTimezoneUpdateMutation';
  timezones?: Maybe<Array<Maybe<RoleTimezoneType>>>;
};

export type RoleType = {
  __typename?: 'RoleType';
  snowflake: Scalars['String'];
  name: Scalars['String'];
  color: Scalars['Int'];
  guild: ServerType;
  perms: Array<Scalars['String']>;
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

export type ServerPermMutation = {
  __typename?: 'ServerPermMutation';
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
  name: Scalars['String'];
  perms: Array<Scalars['String']>;
  prefix: Scalars['String'];
  channels: Array<ChannelType>;
  roles: Array<RoleType>;
  extensions?: Maybe<Array<Maybe<Scalars['String']>>>;
  readable?: Maybe<Array<Scalars['ID']>>;
  writable?: Maybe<Array<Scalars['ID']>>;
};

export type StringTemplateType = {
  __typename?: 'StringTemplateType';
  id: Scalars['ID'];
  source: Scalars['String'];
  server: ServerType;
  name: Scalars['String'];
};

export type UpdateACLMutationVariables = Exact<{
  names: Array<Maybe<Scalars['String']>> | Maybe<Scalars['String']>;
  changes: Array<Maybe<AccessControlInput>> | Maybe<AccessControlInput>;
  serverId: Scalars['ID'];
}>;


export type UpdateACLMutation = (
  { __typename?: 'Mutation' }
  & { deleteACL?: Maybe<(
    { __typename?: 'ACLDeleteMutation' }
    & Pick<ACLDeleteMutation, 'success'>
  )>, updateACL?: Maybe<(
    { __typename?: 'ACLUpdateMutation' }
    & { acl?: Maybe<Array<Maybe<(
      { __typename?: 'AccessControlType' }
      & Pick<AccessControlType, 'name' | 'commands' | 'channels' | 'roles' | 'modifier' | 'action' | 'error'>
    )>>> }
  )> }
);

export type UpdateExtensionsMutationVariables = Exact<{
  serverId: Scalars['ID'];
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

export type UpdateLoggingMutationVariables = Exact<{
  serverId: Scalars['ID'];
  config?: Maybe<Array<Maybe<LoggingEntryInput>> | Maybe<LoggingEntryInput>>;
}>;


export type UpdateLoggingMutation = (
  { __typename?: 'Mutation' }
  & { updateLogging?: Maybe<(
    { __typename?: 'LoggingUpdateMutation' }
    & { logging?: Maybe<Array<Maybe<(
      { __typename?: 'LoggingEntryType' }
      & Pick<LoggingEntryType, 'key' | 'name' | 'channel' | 'role'>
    )>>> }
  )> }
);

export type UpdateModelsMutationVariables = Exact<{
  serverId: Scalars['ID'];
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

export type UpdatePermsMutationVariables = Exact<{
  serverId: Scalars['ID'];
  readable: Array<Scalars['ID']> | Scalars['ID'];
  writable: Array<Scalars['ID']> | Scalars['ID'];
}>;


export type UpdatePermsMutation = (
  { __typename?: 'Mutation' }
  & { updatePerms?: Maybe<(
    { __typename?: 'ServerPermMutation' }
    & { server?: Maybe<(
      { __typename?: 'ServerType' }
      & Pick<ServerType, 'snowflake' | 'readable' | 'writable'>
    )> }
  )> }
);

export type UpdatePrefixMutationVariables = Exact<{
  serverId: Scalars['ID'];
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

export type UpdateTimezonesMutationVariables = Exact<{
  serverId: Scalars['ID'];
  toUpdate?: Maybe<Array<Maybe<RoleTimezoneInput>> | Maybe<RoleTimezoneInput>>;
  toDelete?: Maybe<Array<Maybe<Scalars['String']>> | Maybe<Scalars['String']>>;
}>;


export type UpdateTimezonesMutation = (
  { __typename?: 'Mutation' }
  & { deleteTimezones?: Maybe<(
    { __typename?: 'RoleTimezoneDeleteMutation' }
    & Pick<RoleTimezoneDeleteMutation, 'success'>
  )>, updateTimezones?: Maybe<(
    { __typename?: 'RoleTimezoneUpdateMutation' }
    & { timezones?: Maybe<Array<Maybe<(
      { __typename?: 'RoleTimezoneType' }
      & Pick<RoleTimezoneType, 'roleId' | 'timezone'>
    )>>> }
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

export type LoggingConfigQueryVariables = Exact<{
  serverId: Scalars['ID'];
}>;


export type LoggingConfigQuery = (
  { __typename?: 'Query' }
  & { logging?: Maybe<Array<Maybe<(
    { __typename?: 'LoggingEntryType' }
    & Pick<LoggingEntryType, 'key' | 'name' | 'channel' | 'role'>
  )>>> }
);

export type ServerACLQueryVariables = Exact<{
  serverId: Scalars['ID'];
}>;


export type ServerACLQuery = (
  { __typename?: 'Query' }
  & { acl?: Maybe<Array<Maybe<(
    { __typename?: 'AccessControlType' }
    & Pick<AccessControlType, 'name' | 'commands' | 'channels' | 'roles' | 'modifier' | 'action' | 'error'>
  )>>> }
);

export type ServerDetailsQueryVariables = Exact<{
  serverId: Scalars['ID'];
}>;


export type ServerDetailsQuery = (
  { __typename?: 'Query' }
  & { server?: Maybe<(
    { __typename?: 'ServerType' }
    & Pick<ServerType, 'snowflake' | 'name' | 'prefix' | 'disabled' | 'extensions' | 'perms' | 'readable' | 'writable'>
    & { channels: Array<(
      { __typename?: 'ChannelType' }
      & Pick<ChannelType, 'snowflake' | 'name' | 'type' | 'order'>
      & { category?: Maybe<(
        { __typename?: 'ChannelType' }
        & Pick<ChannelType, 'snowflake'>
      )> }
    )>, roles: Array<(
      { __typename?: 'RoleType' }
      & Pick<RoleType, 'snowflake' | 'name' | 'color' | 'order' | 'perms'>
    )> }
  )> }
);

export type ServerTimezonesQueryVariables = Exact<{
  serverId: Scalars['ID'];
}>;


export type ServerTimezonesQuery = (
  { __typename?: 'Query' }
  & { timezones?: Maybe<Array<Maybe<(
    { __typename?: 'RoleTimezoneType' }
    & Pick<RoleTimezoneType, 'roleId' | 'timezone'>
  )>>> }
);
