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

/** An enumeration. */
export enum AclRoleModifier {
  None = 'NONE',
  Any = 'ANY',
  All = 'ALL'
}

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

export type LoggingEntryType = {
  __typename?: 'LoggingEntryType';
  key?: Maybe<Scalars['String']>;
  name?: Maybe<Scalars['String']>;
  channel?: Maybe<Scalars['String']>;
  role?: Maybe<Scalars['String']>;
};

export type PublicQuery = {
  __typename?: 'PublicQuery';
  server?: Maybe<ServerType>;
  bot?: Maybe<BotType>;
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
  logging?: Maybe<Array<Maybe<LoggingEntryType>>>;
  acl?: Maybe<Array<Maybe<AccessControlType>>>;
};

export type ServerInfoQueryVariables = Exact<{ [key: string]: never; }>;


export type ServerInfoQuery = (
  { __typename?: 'PublicQuery' }
  & { server?: Maybe<(
    { __typename?: 'ServerType' }
    & Pick<ServerType, 'snowflake' | 'name' | 'prefix'>
  )> }
);
