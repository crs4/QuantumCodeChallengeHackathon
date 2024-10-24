import time
import logging
import os.path
import numpy as np
import requests
from typing import Any, Optional
from qbraid.runtime import QbraidClient, QbraidSession, ResourceNotFoundError

from exercise_mod import exercise_type_dict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)



class Crs4GraderClient(QbraidClient):
    TERMINAL_SUBMISSION_STATUSES = ["succeeded", "failed", "cancelled"]

    def __init__(self, api_key: Optional[str] = None, session: Optional[QbraidSession] = None):
        """
        Initializes the IonQ SCQ Client.

        """
        super().__init__(api_key=api_key, session=session)
        self._endpoint = "/crs4"
        self.session.add_user_agent(self.__class__.__name__)
        self.cath_num=["float_list","cplx_list", "intlist", 'nparray', 'nparray_nulti']
        self.cath_files=["file"]
        self.cath_dict=[ "qubo_sol"]
        self.cath_pickle=[]
        

    def check_submission(self,data, quiz):
        c=[]
        exercise_type=exercise_type_dict[quiz]
        c.append(isinstance(data,int) and exercise_type == "number")
        c.append(isinstance(data, str) and exercise_type== "string")
        c.append(isinstance(data,dict) and exercise_type == "qubo_sol") 
        c.append(isinstance(data,str) and exercise_type == "nealsol")
        c.append(isinstance(data,list) and exercise_type == "intlist")
        c.append(isinstance(data, str) and os.path.exists(data) and exercise_type == "file")
        c.append(isinstance(data,list) and isinstance(data[0], float) and exercise_type == "float_list")
        c.append(isinstance(data,list) and isinstance(data[0], complex) and exercise_type == "cplx_list")
        c.append(isinstance(data,list) and exercise_type == "nparray")
        c.append(isinstance(data,list) and  isinstance(data[0], list) and exercise_type == "nparray_multi")
        c.append(isinstance(data,str) and exercise_type == "file")
        if  any(c):
            logger.info("The type of the response you provided is correct")
        else:
            logger.info("The type of the response you provided is not correct. Try again")
            

    def submit_exercise(self, data, quiz):
        team=os.environ.get("TEAM_NAME")
        url = f"{self._endpoint}/submission"
        exercise_type=exercise_type_dict[quiz]
        if exercise_type in self.cath_num:
            data=str(data)
        if exercise_type in self.cath_dict:
            data = str(data)
        if exercise_type in self.cath_pickle:
            data=str(os.path.abspath(data))
        if exercise_type in self.cath_files:
            if not os.path.exists(data):
                logger.error(f"File {data} does not exist")
                raise FileNotFoundError(f"File {data} does not exist")
            data=str(data)
        payload = {'type': exercise_type, 'data': data,'team_name':team, 'task_num':quiz }
        try:
            response = self.session.post(url, json=payload)
            result = response.json()
            logger.info(f"Job completed successfully: {result}")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Error running job: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Server response: {e.response.text}")
            raise
            

    def get_submissions(
        self, submission_id: Optional[str] = None, status: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Retrieves submissions, optionally filtering by submission ID and/or status.

        Args:
            submission_id (Optional[str]): The ID of the submission to retrieve.
            status (Optional[str]): The status of the submission to filter by.

        Returns:
            dict[str, Any]: The response from the server.
        """
        url = f"{self._endpoint}/submission"
        params = {}

        if submission_id:
            params["submissionId"] = submission_id
        if status:
            params["status"] = status

        response = self.session.get(url, params=params)
        return response.json()

    def await_autograder_result(self, submission_id, poll_interval=5, timeout=300):
        """
        Poll the submission status until it reaches a terminal state or times out.

        Args:
            submission_id (str): ID of the submission to poll.
            poll_interval (int): Time (in seconds) between each poll request.
            timeout (int): Maximum time (in seconds) to wait before timing out.

        Returns:
            dict: Final submission data including status and score.
            bool: True if the submission succeeded, False if it failed or timed out.
        """
        start_time = time.time()
        status = None
        score = None
        final_data = None

        logger.info(f"Polling autograder result for submission {submission_id}.")

        while status not in self.TERMINAL_SUBMISSION_STATUSES:
            elapsed_time = time.time() - start_time

            if elapsed_time > timeout:
                raise TimeoutError(f"Polling timed out after {timeout} seconds.")

            try:
                submission_data = self.get_submissions(submission_id=submission_id)[0]
                status = submission_data.get("status")
                message = submission_data.get("statusMessage")
                score = submission_data.get("score", "N/A")
                final_data = submission_data
            except Exception as err:
                raise ResourceNotFoundError(f"Error retrieving submission {submission_id}") from err

            logger.info(
                f"Status: {status}, Message: {message}, Elapsed Time: {elapsed_time:.2f} sec."
            )

            time.sleep(poll_interval)

        logger.info("Polling complete.")

        if status == "succeeded":
            logger.info(f"Submission succeeded with Score: {score}")
            final_data["success"] = True
            return final_data
        else:
            logger.warning(f"Submission failed with final status: {status}.")
            final_data["success"] = False
            return final_data

    def update_submission(
        self,
        submission_id: str,
        status: Optional[str] = None,
        status_message: Optional[str] = None,
        score: Optional[float] = None,
        execution_sec: Optional[float] = None,
    ) -> dict[str, Any]:
        """
        Updates an existing submission.

        Args:
            submission_id (str): The ID of the submission to update.
            status (Optional[str]): The new status.
            status_message (Optional[str]): The new status message.
            score (Optional[float]): The new score.
            execution_sec (Optional[float]): The execution time in seconds.

        Returns:
            dict[str, Any]: The response from the server.
        """
        url = f"{self._endpoint}/submission"
        data = {"submissionId": submission_id}

        if status:
            data["status"] = status
        if status_message:
            data["statusMessage"] = status_message
        if score is not None:
            data["score"] = score
        if execution_sec is not None:
            data["executionSec"] = execution_sec

        response = self.session.put(url, json=data)
        return response.json()

    def create_team(self, team_name: str, team_members: list[str]) -> dict[str, Any]:
        """
        Creates a new team.

        Args:
            team_name (str): The name of the team.
            team_members (list[str]): A list of emails of the team members.

        Returns:
            dict[str, Any]: The response from the server.
        """
        url = f"{self._endpoint}/team"
        data = {"teamName": team_name, "teamMembers": team_members}
        response = self.session.post(url, json=data)
        return response.json()

    def delete_team(self, team_name: str) -> dict[str, Any]:
        """
        Deletes an existing team by name.

        Args:
            team_name (str): The name of the team to delete.

        Returns:
            dict[str, Any]: The response from the server.
        """
        url = f"{self._endpoint}/team/{team_name}"
        response = self.session.delete(url)
        return response.json()

    def add_member_to_team(self, team_name: str, new_member_email: str) -> dict[str, Any]:
        """
        Adds a new member to an existing team.

        Args:
            team_name (str): The name of the team.
            new_member_email (str): The email of the member to add.

        Returns:
            dict[str, Any]: The response from the server.
        """
        url = f"{self._endpoint}/team/{team_name}/add-member"
        data = {"newMemberEmail": new_member_email}
        response = self.session.put(url, json=data)
        return response.json()

    def remove_member_from_team(self, team_name: str, member_email: str) -> dict[str, Any]:
        """
        Removes a member from an existing team.

        Args:
            team_name (str): The name of the team.
            member_email (str): The email of the member to remove.

        Returns:
            dict[str, Any]: The response from the server.
        """
        url = f"{self._endpoint}/team/{team_name}/remove-member"
        data = {"memberEmail": member_email}
        response = self.session.put(url, json=data)
        return response.json()

    def team_status(self, team_name: str) -> dict[str, Any]:
        """
        Retrieves all the metadata associated the given team.

        Args:
            team_name (str): The name of the team.

        Returns:
            dict[str, Any]: The response from the server.
        """
        url = f"{self._endpoint}/team"
        params = {"teamName": team_name}
        response = self.session.get(url, params=params)
        status = response.json()
        if isinstance(status, list) and len(status) == 1:
            return status[0]
        return status

    def change_team_name(self, team_name: str, new_team_name: str) -> dict[str, Any]:
        """
        Changes the name of an existing team.

        Args:
            team_name (str): The current name of the team.
            new_team_name (str): The new name of the team.

        Returns:
            dict[str, Any]: The response from the server.
        """
        url = f"{self._endpoint}/team"
        data = {"teamName": team_name, "newTeamName": new_team_name}
        response = self.session.put(url, json=data)
        return response.json()

def main():
    client = Crs4GraderClient()
    
    

if __name__ == "__main__":
    main()

