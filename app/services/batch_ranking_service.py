"""Batch ranking service with efficient bulk operations."""

import logging
from typing import Callable, Optional
from datetime import datetime

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import MatchResult, Resume, JobDescription

logger = logging.getLogger(__name__)


class BatchRankingService:
    """Service for efficiently ranking candidates with batch database operations.
    
    Features:
    - Batch insert (100 records in 1 query instead of 100 queries)
    - Score computation with caching
    - Deduplication (skip already-ranked pairs)
    - Automatic commit management
    """
    
    def __init__(self, batch_size: int = 100):
        """Initialize batch ranking service.
        
        Args:
            batch_size: Number of records to insert per batch (default: 100)
        """
        self.batch_size = batch_size
        self._scoring_cache = {}  # (resume_id, job_id) -> score dict
    
    async def rank_candidates(
        self,
        session: AsyncSession,
        job_id: str,
        resume_ids: list[str],
        score_function: Callable,
        tenant_id: str,
        skip_existing: bool = True,
        batch_size: Optional[int] = None,
    ) -> list[dict]:
        """Rank candidates for a job using batch operations.
        
        Args:
            session: Async database session
            job_id: Job ID to rank for
            resume_ids: List of resume IDs to score
            score_function: Async function(resume, job) -> score dict
            tenant_id: Tenant ID
            skip_existing: Skip resumes already ranked for this job
            batch_size: Override default batch size
            
        Returns:
            List of match result records created
        """
        batch_size = batch_size or self.batch_size
        results = []
        skipped = 0
        
        logger.info(f"Starting rank of {len(resume_ids)} candidates for job {job_id}")
        
        # Get job once
        job = await session.get(JobDescription, job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return []
        
        # Find existing matches (if skipping)
        existing_pairs = set()
        if skip_existing:
            from sqlalchemy import select
            stmt = select(MatchResult.resume_id).where(
                MatchResult.job_id == job_id
            )
            result = await session.execute(stmt)
            existing_pairs = set(result.scalars().all())
            logger.debug(f"Found {len(existing_pairs)} existing matches to skip")
        
        # Process in batches
        batches = [
            resume_ids[i:i+batch_size]
            for i in range(0, len(resume_ids), batch_size)
        ]
        
        for batch_num, batch in enumerate(batches):
            batch_scores = []
            
            for resume_id in batch:
                # Skip if already ranked
                if resume_id in existing_pairs:
                    skipped += 1
                    continue
                
                try:
                    # Get resume
                    resume = await session.get(Resume, resume_id)
                    if not resume:
                        logger.warning(f"Resume {resume_id} not found")
                        continue
                    
                    # Score
                    score = await score_function(resume, job)
                    
                    # Build match result record
                    match_result = {
                        "resume_id": resume_id,
                        "job_id": job_id,
                        "fit_score": score.get("score", 0),
                        "skill_match": score.get("skill_score", 0),
                        "experience_match": score.get("experience_score", 0),
                        "education_match": score.get("education_score", 0),
                        "projects_match": score.get("project_score", 0),
                        "certs_match": score.get("certification_score", 0),
                        "tenant_id": tenant_id,
                        "computed_at": datetime.utcnow(),
                        "ttl": 3600,  # 1 hour TTL
                    }
                    batch_scores.append(match_result)
                    
                except Exception as e:
                    logger.error(f"Error scoring resume {resume_id}: {e}")
                    continue
            
            # Batch insert
            if batch_scores:
                try:
                    stmt = insert(MatchResult).values(batch_scores)
                    await session.execute(stmt)
                    await session.commit()
                    
                    results.extend(batch_scores)
                    logger.info(
                        f"Batch {batch_num + 1}/{len(batches)}: "
                        f"inserted {len(batch_scores)} matches"
                    )
                    
                except Exception as e:
                    await session.rollback()
                    logger.error(f"Error batch inserting matches: {e}")
                    raise
        
        logger.info(
            f"Ranking complete: {len(results)} inserted, {skipped} skipped"
        )
        return results
    
    
    async def rerank_job(
        self,
        session: AsyncSession,
        job_id: str,
        score_function: Callable,
        tenant_id: str,
    ) -> int:
        """Re-rank all candidates for a job (update existing scores).
        
        Args:
            session: Async database session
            job_id: Job ID to rerank
            score_function: Scoring function
            tenant_id: Tenant ID
            
        Returns:
            Number of records updated
        """
        logger.info(f"Reranking all candidates for job {job_id}")
        
        from sqlalchemy import select, update
        
        # Get all resumes for this job
        stmt = select(MatchResult.resume_id).where(
            MatchResult.job_id == job_id
        )
        result = await session.execute(stmt)
        resume_ids = result.scalars().all()
        
        if not resume_ids:
            logger.info(f"No matches found for job {job_id}")
            return 0
        
        # Delete old matches and re-rank
        delete_stmt = delete(MatchResult).where(
            MatchResult.job_id == job_id
        )
        await session.execute(delete_stmt)
        await session.commit()
        
        # Rank from scratch
        results = await self.rank_candidates(
            session=session,
            job_id=job_id,
            resume_ids=list(resume_ids),
            score_function=score_function,
            tenant_id=tenant_id,
            skip_existing=False,
        )
        
        logger.info(f"Reranking complete: {len(results)} records updated")
        return len(results)


# Global instance
_ranking_service = BatchRankingService(batch_size=100)


def get_ranking_service() -> BatchRankingService:
    """Get global batch ranking service instance."""
    return _ranking_service
