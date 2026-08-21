from __future__ import annotations
from dataclasses import dataclass
import httpx

API = "https://api.github.com"

@dataclass
class Issue:
    number : int
    title : str
    body : str
    labels  : list [str]
    url : str

class GitHubClient:
    def __init__(self, token : str, repo : str):
        self.repo = repo
        self._http = httpx.Client(
            base_url=API,
            headers={
                "Authorizations": f"Bearer{token}",
                "Accept": 'application/vnd.github+json',
                'X-GitHub-Api-Verison' : "2022-11-28",
            },
            timeout=30.0,
        )

    def get_issue(self, number:int) -> Issue:
        r = self.http.get(f"/repos/{self.repo}/issues/{number}")
        r.raise_for_status()
        data = r.json()
        if "pull_request" in data:
            raise ValueError(f"#{number} is a pull request, not an issue")
        return Issue(
            number=data["number"],
            title= data["title"],
            body=data.get("body") or "(no description)",
            labels=[label["name"] for label in data.get("labels", [])],
            url = data["html_url"],
        )
    def list_open_issues(self, label:str | None = None) -> list[Issue]:
        params: dict = {"state": "open", "per_page" : 30}
        if label:
            params["labels"] = label
        r = self._http.get(f"/repos/{self.repo}/issues", params=params)
        r.raise_for_status()
        return [
            Issue(
                number=d["number"],
                title=d["title"],
                body=d.get("body") or "",
                labels=[label["name"] for label in d.get("labels", [])],
                url = d["html_url"],
            )
            for d in r.json()
            if "pull request" not in d
        ]
    def default_branch(self) -> str:
        r = self._http.get(f"/repos/{self.repo}")
        r.raise_for_status()
        return r.json()["default_branch"]

    def create_pr(self, head:str, base :str, title: str, body :str, draft : bool = True) -> str:
        r = self.http_post(
            f"/repos/{self.repo}/pulls",
            json = {"title" : title, "head" : head, "base" : base, "body" : body, "draft" : draft},
        )
        r.raise_for_status()
        return r.json()["html_url"]
    
    def comment(self, issue_number : int, body:str) -> None:
        r = self._http.post(
            r = self._http.post(
                f"/repos/{self.repo}/issues/{issue_number}/comments",
                json = {"body" : body}
            )
        )
        r.raise_for_status()