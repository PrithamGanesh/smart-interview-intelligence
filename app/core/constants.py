"""Application constants and magic values."""

# Scoring Thresholds
EDUCATION_SCORE_NO_MATCH = 0.0
EDUCATION_SCORE_PARTIAL = 0.5
EDUCATION_SCORE_FULL = 1.0

SKILL_SCORE_NO_MATCH = 0.0
SKILL_SCORE_PARTIAL = 0.5
SKILL_SCORE_FULL = 1.0

EXPERIENCE_SCORE_BELOW_MIN = 0.3
EXPERIENCE_SCORE_BELOW_IDEAL = 0.7
EXPERIENCE_SCORE_MEETS_REQUIREMENT = 1.0

PROJECT_SCORE_NOT_FOUND = 0.2
PROJECT_SCORE_FOUND = 0.8

CERT_SCORE_NOT_FOUND = 0.2
CERT_SCORE_FOUND = 0.8

# Matching Thresholds
MINIMUM_FIT_SCORE = 0.3  # Below this, not a viable match
GOOD_FIT_SCORE = 0.7    # Good candidate
EXCELLENT_FIT_SCORE = 0.85  # Excellent candidate

# API Response
REQUEST_ID_HEADER = "X-Request-ID"
CONTENT_TYPE_JSON = "application/json"

# Cache TTLs (in seconds)
CACHE_TTL_RESUME = 3600          # 1 hour
CACHE_TTL_JOB = 86400            # 24 hours
CACHE_TTL_MATCHES = 21600        # 6 hours
CACHE_TTL_EMBEDDINGS = 604800    # 7 days
CACHE_TTL_DASHBOARD = 300        # 5 minutes
CACHE_TTL_RATELIMIT = 60         # 1 minute

# Pagination
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Validation
MIN_RESUME_SIZE_BYTES = 100
MAX_RESUME_SIZE_BYTES = 5 * 1024 * 1024  # 5MB

MIN_JOB_TITLE_LENGTH = 3
MAX_JOB_TITLE_LENGTH = 255

MIN_JOB_DESCRIPTION_LENGTH = 50
MAX_JOB_DESCRIPTION_LENGTH = 10000

# Text Processing
MIN_SKILL_NAME_LENGTH = 2
MAX_SKILL_NAME_LENGTH = 100

SKILL_NORMALIZATION_RULES = {
    "python": ["py", "python3", "python2"],
    "javascript": ["js", "node", "nodejs"],
    "typescript": ["ts"],
    "react": ["reactjs", "react.js"],
    "vue": ["vuejs", "vue.js"],
    "angular": ["angularjs", "angular.js"],
    "docker": ["dockerization"],
    "kubernetes": ["k8s"],
    "aws": ["amazon", "amazon web services"],
    "gcp": ["google cloud", "google cloud platform"],
    "azure": ["microsoft azure", "azure"],
    "sql": ["sql server", "t-sql"],
    "nosql": ["nosql databases"],
    "postgres": ["postgresql", "postgres"],
    "mysql": ["mysql database"],
    "mongodb": ["mongo", "mongodb"],
}

# Success Prediction Model
SUCCESS_PREDICTION_THRESHOLD = 0.6  # Probability threshold for "likely to succeed"

# ML Model Versions
EMBEDDING_MODEL_VERSION = "all-MiniLM-L6-v2"
SUCCESS_MODEL_VERSION = "1.0.0"

# Error Messages
ERROR_RESUME_NOT_FOUND = "Resume not found"
ERROR_JOB_NOT_FOUND = "Job not found"
ERROR_INVALID_FILE_TYPE = "Invalid file type. Allowed: PDF, DOCX, TXT"
ERROR_FILE_TOO_LARGE = "File size exceeds maximum allowed size"
ERROR_INVALID_PAGE_PARAMS = "Invalid pagination parameters"
ERROR_UNAUTHORIZED = "Unauthorized access"
ERROR_RATE_LIMITED = "Rate limit exceeded"
ERROR_INTERNAL_ERROR = "Internal server error"

# Success Messages
SUCCESS_RESUME_UPLOADED = "Resume uploaded successfully"
SUCCESS_JOB_CREATED = "Job created successfully"
SUCCESS_MATCH_COMPUTED = "Matches computed successfully"
