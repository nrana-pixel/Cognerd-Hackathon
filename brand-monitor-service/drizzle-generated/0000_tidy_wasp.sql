CREATE TYPE "public"."role" AS ENUM('user', 'assistant');--> statement-breakpoint
CREATE TYPE "public"."theme" AS ENUM('light', 'dark');--> statement-breakpoint
CREATE TABLE "aeo_reports" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"user_id" text,
	"user_email" text,
	"customer_name" text NOT NULL,
	"url" text NOT NULL,
	"html" text,
	"read" boolean DEFAULT false,
	"created_at" timestamp DEFAULT now()
);
--> statement-breakpoint
CREATE TABLE "brand_analyses" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"user_id" text NOT NULL,
	"url" text NOT NULL,
	"company_name" text,
	"industry" text,
	"analysis_data" jsonb,
	"competitors" jsonb,
	"prompts" jsonb,
	"credits_used" integer DEFAULT 10,
	"created_at" timestamp DEFAULT now(),
	"updated_at" timestamp DEFAULT now()
);
--> statement-breakpoint
CREATE TABLE "brand_profile" (
	"id" uuid PRIMARY KEY NOT NULL,
	"user_id" text NOT NULL,
	"brand_name" text NOT NULL,
	"brandurl" text NOT NULL,
	"industry" text NOT NULL,
	"location" text DEFAULT 'Global',
	"email" text,
	"logo" text,
	"favicon" text,
	"description" text,
	"competitors" jsonb,
	"scraped_data" jsonb,
	"is_scraped" boolean DEFAULT false,
	"created_at" timestamp DEFAULT now(),
	"updated_at" timestamp DEFAULT now(),
	CONSTRAINT "brand_profile_id_unique" UNIQUE("id"),
	CONSTRAINT "brand_profile_user_id_brandurl_unique" UNIQUE("user_id","brandurl")
);
--> statement-breakpoint
CREATE TABLE "conversations" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"user_id" text NOT NULL,
	"title" text,
	"last_message_at" timestamp,
	"created_at" timestamp DEFAULT now(),
	"updated_at" timestamp DEFAULT now()
);
--> statement-breakpoint
CREATE TABLE "message_feedback" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"message_id" uuid NOT NULL,
	"user_id" text NOT NULL,
	"rating" integer,
	"feedback" text,
	"created_at" timestamp DEFAULT now()
);
--> statement-breakpoint
CREATE TABLE "messages" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"conversation_id" uuid NOT NULL,
	"user_id" text NOT NULL,
	"role" "role" NOT NULL,
	"content" text NOT NULL,
	"token_count" integer,
	"created_at" timestamp DEFAULT now()
);
--> statement-breakpoint
CREATE TABLE "user" (
	"id" text PRIMARY KEY NOT NULL,
	"name" text,
	"email" text NOT NULL,
	"emailVerified" boolean NOT NULL,
	"image" text,
	"createdAt" timestamp NOT NULL,
	"updatedAt" timestamp NOT NULL,
	CONSTRAINT "user_email_unique" UNIQUE("email")
);
--> statement-breakpoint
CREATE TABLE "user_profile" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"user_id" text NOT NULL,
	"display_name" text,
	"avatar_url" text,
	"bio" text,
	"phone" text,
	"created_at" timestamp DEFAULT now(),
	"updated_at" timestamp DEFAULT now(),
	CONSTRAINT "user_profile_user_id_unique" UNIQUE("user_id")
);
--> statement-breakpoint
CREATE TABLE "user_settings" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"user_id" text NOT NULL,
	"theme" "theme" DEFAULT 'light',
	"email_notifications" boolean DEFAULT true,
	"marketing_emails" boolean DEFAULT false,
	"default_model" text DEFAULT 'gpt-3.5-turbo',
	"metadata" jsonb,
	"created_at" timestamp DEFAULT now(),
	"updated_at" timestamp DEFAULT now(),
	CONSTRAINT "user_settings_user_id_unique" UNIQUE("user_id")
);
--> statement-breakpoint
CREATE TABLE "blogs" (
	"id" serial PRIMARY KEY NOT NULL,
	"company_url" text NOT NULL,
	"email_id" text,
	"brand_name" text,
	"blog" text NOT NULL,
	"twitter_post" text,
	"linkedin_post" text,
	"reddit_post" text,
	"user_id" text,
	"status" text DEFAULT 'PENDING',
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"topic" text
);
--> statement-breakpoint
CREATE TABLE "file_generation_jobs" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"user_id" text NOT NULL,
	"user_email" text NOT NULL,
	"url" text NOT NULL,
	"brand" text,
	"category" text,
	"competitors" jsonb,
	"prompts" text,
	"status" text DEFAULT 'pending' NOT NULL,
	"nonce" text NOT NULL,
	"result" jsonb,
	"error" text,
	"webhook_attempted_at" timestamp,
	"webhook_response_code" text,
	"created_at" timestamp DEFAULT now(),
	"updated_at" timestamp DEFAULT now()
);
--> statement-breakpoint
CREATE TABLE "files" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"user_id" text NOT NULL,
	"user_email" text NOT NULL,
	"brand" text,
	"url" text,
	"llms" text,
	"robots" text,
	"site_schema" text,
	"faqs" text,
	"created_at" timestamp DEFAULT now()
);
--> statement-breakpoint
CREATE TABLE "topic_suggestions" (
	"id" serial PRIMARY KEY NOT NULL,
	"email_id" text,
	"brand_name" text NOT NULL,
	"topics" jsonb NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "notifications" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"user_id" text,
	"user_email" text,
	"type" text NOT NULL,
	"message" text NOT NULL,
	"link" text,
	"asset_id" text,
	"asset_table" text,
	"status" text DEFAULT 'not_sent' NOT NULL,
	"read" boolean DEFAULT false NOT NULL,
	"created_at" timestamp DEFAULT now()
);
--> statement-breakpoint
ALTER TABLE "message_feedback" ADD CONSTRAINT "message_feedback_message_id_messages_id_fk" FOREIGN KEY ("message_id") REFERENCES "public"."messages"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "messages" ADD CONSTRAINT "messages_conversation_id_conversations_id_fk" FOREIGN KEY ("conversation_id") REFERENCES "public"."conversations"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
CREATE UNIQUE INDEX "topic_suggestions_email_id_brand_name_key" ON "topic_suggestions" USING btree ("email_id","brand_name");