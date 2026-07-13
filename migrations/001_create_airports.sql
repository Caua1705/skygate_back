create extension if not exists pgcrypto;

create table if not exists airports (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    slug text not null unique,
    city text,
    country text,
    created_at timestamptz default now()
);

