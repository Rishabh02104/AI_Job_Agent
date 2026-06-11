import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.tracker import TrackerAgent
from agents.base import AgentResult

class TestTrackerAgent(unittest.TestCase):
    @patch('agents.tracker.Groq')
    @patch('agents.tracker.supabase')
    def test_classify_email_interview(self, mock_supabase, mock_groq):
        # Setup mocks
        agent = TrackerAgent()
        
        # Mock active applications context
        active_apps = [
            {
                "id": "app-123",
                "status": "applied",
                "jobs": {
                    "title": "AI Engineer",
                    "company": "NextGen AI Labs"
                }
            }
        ]
        
        # Mock Groq client response
        mock_client = MagicMock()
        mock_groq.return_value = mock_client
        
        mock_completion = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        
        mock_message = MagicMock()
        mock_message.content = """
        {
          "matched": true,
          "application_id": "app-123",
          "status": "interview",
          "reason": "Candidate invited to technical interview round."
        }
        """
        mock_completion.choices = [MagicMock(message=mock_message)]
        
        # Test classification function
        res = agent._classify_email_with_groq(
            client=mock_client,
            sender="hr@nextgenailabs.com",
            subject="Interview Invitation - NextGen AI Labs",
            body="Hi Rishabh, we would love to invite you for an interview next week.",
            active_apps=active_apps
        )
        
        self.assertTrue(res["matched"])
        self.assertEqual(res["application_id"], "app-123")
        self.assertEqual(res["status"], "interview")
        self.assertEqual(res["reason"], "Candidate invited to technical interview round.")

    @patch('agents.tracker.Groq')
    def test_classify_email_rejection(self, mock_groq):
        agent = TrackerAgent()
        active_apps = [
            {
                "id": "app-456",
                "status": "applied",
                "jobs": {
                    "title": "Software Engineer",
                    "company": "TechCorp"
                }
            }
        ]
        
        mock_client = MagicMock()
        mock_groq.return_value = mock_client
        
        mock_completion = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        
        mock_message = MagicMock()
        mock_message.content = """
        {
          "matched": true,
          "application_id": "app-456",
          "status": "rejected",
          "reason": "Email states candidacy will not be advanced."
        }
        """
        mock_completion.choices = [MagicMock(message=mock_message)]
        
        res = agent._classify_email_with_groq(
            client=mock_client,
            sender="no-reply@techcorp.com",
            subject="Update on your application",
            body="Thank you for your application, however we have decided to move forward with other candidates.",
            active_apps=active_apps
        )
        
        self.assertTrue(res["matched"])
        self.assertEqual(res["application_id"], "app-456")
        self.assertEqual(res["status"], "rejected")

if __name__ == '__main__':
    unittest.main()
