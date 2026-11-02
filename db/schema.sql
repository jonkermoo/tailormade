-- TailorMade schema, first draft (Azure SQL Database / T-SQL)

CREATE TABLE users (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    auth_user_id    NVARCHAR(200) NOT NULL UNIQUE,   -- from Static Web Apps sign-in
    email           NVARCHAR(320) NULL,
    display_name    NVARCHAR(200) NULL,
    profile_json    NVARCHAR(MAX) NULL,              -- structured resume profile
    created_at      DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);

-- One row per real-world job, no matter how many sites list it
CREATE TABLE jobs (
    id              BIGINT IDENTITY(1,1) PRIMARY KEY,
    dedupe_hash     CHAR(64) NOT NULL,               -- SHA-256 of company|title|city
    company         NVARCHAR(200) NOT NULL,
    title           NVARCHAR(300) NOT NULL,
    location        NVARCHAR(300) NULL,
    is_remote       BIT NOT NULL DEFAULT 0,
    description     NVARCHAR(MAX) NULL,
    posted_at       DATETIME2 NULL,
    first_seen_at   DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    last_seen_at    DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT uq_jobs_dedupe_hash UNIQUE (dedupe_hash)
);

CREATE INDEX ix_jobs_first_seen ON jobs (first_seen_at DESC);
CREATE INDEX ix_jobs_company ON jobs (company);

-- Every place a job was found (Greenhouse, Lever, Adzuna...)
CREATE TABLE job_sources (
    id              BIGINT IDENTITY(1,1) PRIMARY KEY,
    job_id          BIGINT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    source          NVARCHAR(50) NOT NULL,
    source_job_id   NVARCHAR(200) NOT NULL,
    url             NVARCHAR(1000) NOT NULL,
    fetched_at      DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT uq_job_sources UNIQUE (source, source_job_id)
);

CREATE TABLE saved_filters (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    user_id         INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name            NVARCHAR(100) NOT NULL,
    keywords        NVARCHAR(500) NULL,              -- comma separated
    locations       NVARCHAR(500) NULL,
    remote_only     BIT NOT NULL DEFAULT 0,
    min_score       TINYINT NOT NULL DEFAULT 70,     -- alert threshold
    alerts_enabled  BIT NOT NULL DEFAULT 1,
    created_at      DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);

-- Tailored resumes; the PDF itself lives in Blob Storage
CREATE TABLE resume_versions (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    user_id         INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id          BIGINT NULL REFERENCES jobs(id),
    blob_path       NVARCHAR(500) NOT NULL,
    match_score     TINYINT NULL,
    missing_skills  NVARCHAR(1000) NULL,
    created_at      DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);

CREATE TABLE applications (
    id                  INT IDENTITY(1,1) PRIMARY KEY,
    user_id             INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id              BIGINT NOT NULL REFERENCES jobs(id),
    resume_version_id   INT NULL REFERENCES resume_versions(id),
    status              NVARCHAR(20) NOT NULL DEFAULT 'saved'
        CHECK (status IN ('saved', 'applied', 'interview', 'offer', 'rejected')),
    notes               NVARCHAR(2000) NULL,
    applied_at          DATETIME2 NULL,
    updated_at          DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT uq_applications_user_job UNIQUE (user_id, job_id)
);

-- Index for filtering job listings
CREATE INDEX ix_jobs_feed
ON jobs (posted_at DESC, is_remote, location);

-- Index for tracking applications by user and status
CREATE INDEX ix_applications_user_status
ON applications (user_id, status);

