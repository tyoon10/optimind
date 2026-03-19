import os
import datetime
from typing import List, Optional
from src.config import config
try:
    from git import Repo, GitCommandError
except ImportError:
    Repo = None # Fallback if GitPython missing

class JournalManager:
    """
    Manages the flat-file markdown journal system.
    Daily logs are stored in data/journal/YYYY-MM-DD.md.
    """
    
    def __init__(self, journal_dir: str = "data/journal"):
        # Make path relative to base if not absolute
        if not os.path.isabs(journal_dir):
            self.journal_dir = os.path.join(config.BASE_DIR, journal_dir)
        else:
            self.journal_dir = journal_dir
            
        # Prevent Git from hanging on auth prompts (Critical for Headless/Cloud)
        os.environ["GIT_TERMINAL_PROMPT"] = "0"
            
        self.repo = None
        
    def initialize_repo(self):
        """
        Explicit initialization to allow async/delayed startup in Cloud.
        Attempts to Clone if repo missing, or Attach if exists.
        """
        print(f"DEBUG: Initializing JournalManager at {self.journal_dir}")
        
        # 1. Try to attach to existing repo (Local Dev case or Persistent Cloud Volume)
        if os.path.exists(os.path.join(self.journal_dir, ".git")):
            try:
                self.repo = Repo(self.journal_dir)
                print(f"DEBUG: Attached to existing Git repo at {self.journal_dir}")
                # Do NOT return here, we must still configure auth below
            except Exception as e:
                print(f"WARNING: Failed to attach to existing repo: {e}")

        # Always ensure directory exists to prevent FileNotFoundError in log_interaction
        os.makedirs(self.journal_dir, exist_ok=True)

        # 2. If no repo, try to CLONE (Cloud Run fresh start)
        if not self.repo and config.GITHUB_PAT and config.JOURNAL_REPO_URL:
            try:
                # Inject PAT into URL for auth: https://PAT@github.com/user/repo.git
                auth_url = config.JOURNAL_REPO_URL.replace("https://", f"https://{config.GITHUB_PAT}@")
                
                print(f"DEBUG: Cloning journal from {config.JOURNAL_REPO_URL}...")
                
                # Check for existing empty dir (created above or by volume mount)
                if os.path.exists(os.path.join(self.journal_dir, ".git")):
                     print("DEBUG: Found existing .git in target dir. Attaching...")
                     self.repo = Repo(self.journal_dir)
                else:
                     # GitPython clone_from requires empty dir or non-existent dir usually, 
                     # but if we created it empty above, we might need to handle it.
                     # Actually, clone_from to an empty existing dir works fine.
                     self.repo = Repo.clone_from(auth_url, self.journal_dir)
                
                # Configure Bot Identity
                with self.repo.config_writer() as git_config:
                    git_config.set_value("user", "name", "OptiMind Bot")
                    git_config.set_value("user", "email", "bot@optimind.ai")
                    
                print("DEBUG: Clone successful.")
            except Exception as e:
                print(f"ERROR: Failed to clone repo: {e}")
        elif not self.repo:
            print("WARNING: No GITHUB_PAT or JOURNAL_REPO_URL provided. Running in memory-only mode.")

        # CRITICAL FIX: Ensure Remote URL always has PAT (even if attached or cloned)
        if self.repo and config.GITHUB_PAT and config.JOURNAL_REPO_URL:
            try:
                auth_url = config.JOURNAL_REPO_URL.replace("https://", f"https://{config.GITHUB_PAT}@")
                # Set origin to auth_url
                # Set origin to auth_url safely (preserving tracking)
                if "origin" in self.repo.remotes:
                    remote = self.repo.remote("origin")
                    remote.set_url(auth_url)
                    # remote.set_url(auth_url, old_url=remote.url) # Safety check if needed
                else:
                     self.repo.create_remote("origin", auth_url)
                print("DEBUG: Secured Remote Origin with PAT (Tracking Preserved).")
            except Exception as e:
                print(f"ERROR: Failed to update remote origin: {e}")

    def _get_daily_file_path(self, date: Optional[datetime.date] = None) -> str:
        """Get the absolute path for a specific date's log file."""
        if date is None:
            # FIX: Use EST date to ensure files match user's day
            try:
                import pytz
                tz = pytz.timezone('US/Eastern')
                date = datetime.datetime.now(tz).date()
            except ImportError:
                date = datetime.date.today()
                
        filename = f"{date.isoformat()}.md"
        return os.path.join(self.journal_dir, filename)

    def sync(self, push: bool = True):
        """
        Public Sync Method.
        push=False -> Pull Only (Start of session)
        push=True -> Commit & Push (End of session)
        """
        if not self.repo:
            return

        try:
            # 1. Pull (Always pull to avoid conflicts/get latest)
            print("DEBUG: Git Pull...")
            self.repo.git.pull("origin", "main")
            
            if push:
                # 2. Add & Commit
                if self.repo.is_dirty(path=self.journal_dir) or self.repo.untracked_files:
                    # Generic commit message for the session
                    msg = f"Journal Sync {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
                    self.repo.git.add(self.journal_dir)
                    self.repo.index.commit(msg)
                    print(f"DEBUG: Committed: {msg}")
                
                # 3. Push
                print("DEBUG: Git Push...")
                self.repo.git.push()
                print("DEBUG: Push successful.")
                
        except Exception as e:
            print(f"ERROR: Git Sync Failed: {e}")

    def log_interaction(self, role: str, content: str, hidden_context: str = None):
        """
        Append a message to today's log.
        Writes LOCALLY only. Requires manual sync() call to persist to cloud.
        """
        filepath = self._get_daily_file_path()
        
        # FIX: Use EST instead of System Time (UTC)
        try:
            import pytz
            tz = pytz.timezone('US/Eastern')
            timestamp = datetime.datetime.now(tz).strftime("%H:%M")
        except ImportError:
            timestamp = datetime.datetime.now().strftime("%H:%M")
        
        entry = f"\n### {timestamp} | {role}\n{content}\n"
        if hidden_context:
            entry += f"<!-- Context: {hidden_context} -->\n"
            
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                existing_content = f.read()
                
            # Fail-safe Deduplication
            if content.strip() in existing_content[-len(content)*2:]:
                print(f"DEBUG: Generic deduplication triggered for content: {content[:20]}...")
                return

        with open(filepath, "a", encoding="utf-8") as f:
            f.write(entry)
            
    def get_recent_context(self, days: int = 7) -> str:
        """
        Read the last N days of logs into a single context string.
        LOCALLY reads only. Requires manual sync() call to get latest from cloud.
        """
        context_parts = []
        try:
            import pytz
            tz = pytz.timezone('US/Eastern')
            today = datetime.datetime.now(tz).date()
        except ImportError:
            today = datetime.date.today()
        
        # Iterate backwards from today
        for i in range(days):
            date = today - datetime.timedelta(days=i)
            filepath = self._get_daily_file_path(date)
            
            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                    header = f"\n\n=== JOURNAL LOG: {date.isoformat()} ===\n"
                    context_parts.append(header + content)
        
        # Reverse so oldest day is first, today is last
        context_parts.reverse()
        
        return "".join(context_parts)

# Global Instance
journal_manager = JournalManager()
