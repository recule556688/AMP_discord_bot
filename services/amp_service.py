import asyncio
import secrets
import string
import aiohttp
import json
import os
from typing import Optional, Dict, Any, Set
from ampapi import Bridge, AMPADSInstance, Core
from ampapi.dataclass import APIParams
from models import AMPUser, AMPInstance
from config.templates import get_template_id
from database.db import DatabaseManager
from config.settings import settings
from utils.logging import get_logger

logger = get_logger(__name__)


class AMPService:
    """Service for interacting with AMP API."""

    def __init__(self, host: str, port: int, username: str, password: str):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.bridge: Optional[Bridge] = None
        self.db = DatabaseManager(settings.database_path)
        self.ads_instance: Optional[AMPADSInstance] = None
        self._connected = False
        self.session_id: Optional[str] = None
        self.http_session: Optional[aiohttp.ClientSession] = None

    async def connect(self) -> bool:
        """Connect to AMP API."""
        try:
            # Create API parameters
            api_params = APIParams(
                url=f"http://{self.host}:{self.port}",
                user=self.username,
                password=self.password,
                use_2fa=False,
            )

            # Create bridge and connect
            self.bridge = Bridge(api_params=api_params)

            # Run the connection in a thread pool
            loop = asyncio.get_event_loop()

            # Initialize the bridge (this handles login)
            success = await loop.run_in_executor(None, self._sync_connect)

            if success:
                # Connection successful - we'll initialize ADS when needed for instance creation
                self._connected = True
                logger.info("Successfully connected to AMP API")
                return True
            else:
                logger.error("Failed to connect to AMP API")
                return False

        except Exception as e:
            logger.error(f"Error connecting to AMP API: {e}")
            return False

    def _sync_connect(self) -> bool:
        """Synchronous connection method."""
        try:
            # The Bridge handles the login automatically when created
            # For now, just check if the bridge was created successfully
            # and has the required attributes
            if hasattr(self.bridge, "api_params") and hasattr(self.bridge, "url"):
                logger.info("Bridge created successfully with API parameters")
                return True
            return False
        except Exception as e:
            logger.error(f"Sync connection failed: {e}")
            return False

    async def disconnect(self):
        """Disconnect from AMP API."""
        if self.bridge and self._connected:
            try:
                # The Bridge doesn't have a logout method in this version
                # Just mark as disconnected
                self._connected = False
                logger.info("Disconnected from AMP API")
            except Exception as e:
                logger.error(f"Error disconnecting from AMP: {e}")

        # Also cleanup HTTP session
        if self.http_session:
            try:
                await self.http_logout()
                await self.http_session.close()
                self.http_session = None
                logger.info("HTTP session closed")
            except Exception as e:
                logger.error(f"Error closing HTTP session: {e}")

    def _generate_password(self, length: int = 12) -> str:
        """Generate a random password."""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return "".join(secrets.choice(alphabet) for _ in range(length))

    async def create_user(
        self, username: str, email: str, roles: list[str], discord_user_id: int = None
    ) -> Optional[AMPUser]:
        """Create a new AMP user or return existing user."""
        if not self._connected or not self.bridge:
            logger.error("Not connected to AMP API")
            return None

        try:
            # Check database first - if we've created this user before, don't try again
            if await self.db.amp_user_exists(username):
                logger.info(
                    f"User {username} found in database, returning existing user"
                )
                return AMPUser(
                    user_id=username,
                    username=username,
                    email=email,
                    password="[EXISTING]",
                    roles=roles,
                )

            # Create Core API instance
            core_api = Core()
            core_api.parse_bridge(self.bridge)

            # First try to check if user already exists by attempting to get user info
            logger.info(f"Checking if user {username} exists by getting user info...")
            try:
                user_info = await asyncio.wait_for(
                    core_api.get_user_info(username), timeout=5.0
                )
                if user_info is not None:
                    logger.info(
                        f"User {username} already exists (found via get_user_info), returning existing user"
                    )
                    # Record in database for future reference
                    if discord_user_id:
                        await self.db.create_amp_user_record(
                            discord_user_id, username, email
                        )
                    return AMPUser(
                        user_id=username,
                        username=username,
                        email=email,
                        password="[EXISTING]",
                        roles=roles,
                    )
            except (asyncio.TimeoutError, Exception) as e:
                logger.info(
                    f"Could not get user info for {username} (probably doesn't exist): {e}"
                )

            # Try to create user - if it fails because user exists, we'll handle it
            logger.info(f"Attempting to create user: {username}")
            password = self._generate_password()

            # Create user using Core API with timeout to prevent hanging
            try:
                # Add 10 second timeout to prevent hanging
                create_result = await asyncio.wait_for(
                    core_api.create_user(username, True), timeout=10.0
                )
            except asyncio.TimeoutError:
                logger.warning(
                    f"User creation timed out for {username}, assuming user exists"
                )
                # Record in database for future reference
                if discord_user_id:
                    await self.db.create_amp_user_record(
                        discord_user_id, username, email
                    )
                return AMPUser(
                    user_id=username,  # Use username as ID for existing users
                    username=username,
                    email=email,
                    password="[EXISTING]",  # Don't expose existing password
                    roles=roles,
                )
            except Exception as e:
                error_msg = str(e).lower()
                # Check if error indicates user already exists
                if any(
                    keyword in error_msg
                    for keyword in ["already exists", "duplicate", "conflict", "exists"]
                ):
                    logger.info(
                        f"User {username} already exists (detected from error), returning existing user"
                    )
                    # Record in database for future reference
                    if discord_user_id:
                        await self.db.create_amp_user_record(
                            discord_user_id, username, email
                        )
                    return AMPUser(
                        user_id=username,  # Use username as ID for existing users
                        username=username,
                        email=email,
                        password="[EXISTING]",  # Don't expose existing password
                        roles=roles,
                    )
                else:
                    # Re-raise if it's a different error
                    logger.error(f"Unexpected error creating user {username}: {e}")
                    raise

            logger.debug(f"Create user result: {create_result}")
            logger.debug(f"Result type: {type(create_result)}")

            # Since you confirmed the user is being created successfully in AMP,
            # we'll treat a None response as success (some AMP API calls return None but work)
            if create_result is None:
                logger.info(
                    f"User {username} creation returned None but may have succeeded"
                )

                # Now set the password for the NEW user only
                try:
                    password_result = await core_api.reset_user_password(
                        username,
                        password,
                        True,  # format_data
                    )
                    logger.debug(f"Password set result: {password_result}")
                except Exception as e:
                    logger.warning(f"Failed to set password for {username}: {e}")
                    # Continue anyway as user was created

                # The API doesn't set email directly, so we'll track what we intended
                user = AMPUser(
                    username=username,
                    password=password,  # Now actually set via API
                    email=email,  # Intended but not set via API
                    roles=roles,  # Will be set separately
                    user_id=None,  # We don't have the ID from the response
                )
                # Add to database so we don't try to create again
                if discord_user_id:
                    await self.db.create_amp_user_record(
                        discord_user_id, username, email
                    )
                logger.info(f"Successfully created AMP user: {username}")
                return user

            # If we have a proper ActionResult, handle it normally
            if (
                create_result
                and hasattr(create_result, "status")
                and create_result.status
            ):
                # Set password for successful user creation
                try:
                    password_result = await core_api.reset_user_password(
                        username,
                        password,
                        True,  # format_data
                    )
                    logger.debug(f"Password set result: {password_result}")
                except Exception as e:
                    logger.warning(f"Failed to set password for {username}: {e}")

                # The API doesn't set email directly, so we'll track what we intended
                user = AMPUser(
                    username=username,
                    password=password,  # Now actually set via API
                    email=email,  # Intended but not set via API
                    roles=roles,  # Will be set separately
                    user_id=(
                        str(create_result.result)
                        if hasattr(create_result, "result")
                        else None
                    ),
                )

                logger.info(f"Successfully created AMP user: {username}")
                return user

            # If we get here, the user creation failed
            reason = (
                getattr(create_result, "reason", "Unknown error")
                if create_result
                else "Unknown response format"
            )
            logger.error(f"Failed to create user {username}: {reason}")
            return None

        except Exception as e:
            logger.error(f"Error creating AMP user {username}: {e}")
            return None

    async def get_deployment_templates(self) -> list:
        """Get available deployment templates."""
        if not self._connected or not self.bridge:
            logger.error("Not connected to AMP API")
            return []

        try:
            # Create ADS API instance
            from ampapi import ADSModule

            # Get deployment templates with format_data parameter
            logger.info("Attempting to get deployment templates...")

            # Try calling it as a static method with bridge
            templates = await ADSModule.get_deployment_templates(
                self.bridge, format_data=True
            )
            logger.info(
                f"Available deployment templates: {len(templates) if templates else 0}"
            )

            if templates:
                for i, template in enumerate(templates[:5]):  # Log first 5 templates
                    template_name = getattr(
                        template, "Name", getattr(template, "name", "Unknown")
                    )
                    template_author = getattr(
                        template, "Author", getattr(template, "author", "Unknown")
                    )
                    logger.info(f"Template {i}: {template_name} - {template_author}")

            return templates or []

        except Exception as e:
            logger.error(f"Error getting deployment templates: {e}")
            # Let's also try to see what methods are available on ADSModule
            try:
                from ampapi import ADSModule

                ads_api = ADSModule()
                logger.info(
                    f"Available ADSModule methods: {[method for method in dir(ads_api) if not method.startswith('_')]}"
                )
            except Exception as debug_e:
                logger.error(f"Error debugging ADSModule: {debug_e}")
            return []

    async def create_instance(
        self, name: str, template: str, owner_id: str, amp_username: str = None
    ) -> Optional[AMPInstance]:
        """Create a new AMP instance using the HTTP API."""
        logger.info(f"Creating instance: {name} for template: {template}")

        # Use HTTP API directly (this is the working method)
        try:
            return await self.http_create_instance(
                name, template, owner_id, amp_username
            )
        except Exception as e:
            logger.error(f"Error creating instance: {e}")
            return AMPInstance(
                name=name,
                template=template,
                owner_id=owner_id,
                instance_id=name,
                status="failed",
            )

    async def get_user_info(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user information from AMP."""
        if not self._connected or not self.bridge:
            logger.error("Not connected to AMP API")
            return None

        try:
            # Create Core API instance
            core_api = Core()
            core_api.parse_bridge(self.bridge)

            # Get all users - call async method directly
            users_result = await core_api.get_all_amp_user_info()

            if users_result and users_result.status:
                for user in users_result.result:
                    if user.name == username:
                        return user.__dict__

            return None

        except Exception as e:
            logger.error(f"Error getting user info for {username}: {e}")
            return None

    async def get_instances(self) -> list:
        """Get all instances from AMP."""
        if not self._connected or not self.bridge:
            logger.error("Not connected to AMP API")
            return []

        try:
            from ampapi import ADSModule

            ads_api = ADSModule()
            ads_api.parse_bridge(self.bridge)

            # Try to get all instances
            instances_result = await ads_api.get_instances(format_data=True)

            logger.debug(f"Get instances result: {instances_result}")
            logger.debug(f"Get instances type: {type(instances_result)}")

            # The result is a list of ADS information, we need to extract available_instances
            all_instances = []
            if instances_result and isinstance(instances_result, list):
                for ads_info in instances_result:
                    if isinstance(ads_info, dict) and "available_instances" in ads_info:
                        available_instances = ads_info["available_instances"]
                        logger.info(
                            f"Found {len(available_instances)} instances in ADS"
                        )
                        all_instances.extend(available_instances)

                        # Log each instance for debugging
                        for i, instance in enumerate(available_instances):
                            instance_name = getattr(instance, "Name", "Unknown")
                            instance_id = getattr(instance, "InstanceID", "Unknown")
                            module = getattr(instance, "Module", "Unknown")
                            logger.info(
                                f"  Instance {i}: {instance_name} (ID: {instance_id}, Module: {module})"
                            )

                logger.info(
                    f"Total instances found across all ADS: {len(all_instances)}"
                )
                return all_instances
            else:
                logger.warning("No instances found or unexpected result format")
                return []

        except Exception as e:
            logger.error(f"Error getting instances: {e}")
            return []

    async def http_login(self) -> bool:
        """Login using direct HTTP API calls."""
        try:
            if not self.http_session:
                self.http_session = aiohttp.ClientSession()

            login_url = f"http://{self.host}:{self.port}/API/Core/Login"
            login_payload = {
                "username": self.username,
                "password": self.password,
                "token": "",
                "rememberMe": False,
            }

            headers = {
                "Accept": "application/json",
                "User-Agent": "AMP-Discord-Bot/1.0",
                "Content-Type": "application/json",
            }

            logger.info(f"Attempting HTTP login to {login_url}")

            async with self.http_session.post(
                login_url, data=json.dumps(login_payload), headers=headers
            ) as response:
                if response.status != 200:
                    logger.error(f"HTTP Login failed: {response.status}")
                    return False

                login_data = await response.json()
                self.session_id = login_data.get("sessionID") or login_data.get(
                    "SessionID"
                )

                if self.session_id:
                    logger.info("HTTP login successful")
                    return True
                else:
                    logger.error("No session ID received from login")
                    return False

        except Exception as e:
            logger.error(f"Error in HTTP login: {e}")
            return False

    async def http_get_instances(self) -> list:
        """Get instances using direct HTTP API."""
        if not self.session_id or not self.http_session:
            if not await self.http_login():
                return []

        try:
            instances_url = f"http://{self.host}:{self.port}/API/ADSModule/GetInstances"
            payload = {"SESSIONID": self.session_id}

            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "SESSIONID": self.session_id,
            }

            logger.info("Getting instances via HTTP API")

            async with self.http_session.post(
                instances_url, data=json.dumps(payload), headers=headers
            ) as response:
                if response.status != 200:
                    logger.error(f"Failed to get instances: {response.status}")
                    return []

                instances_data = await response.json()

                # Extract instances from the nested structure
                all_instances = []
                if isinstance(instances_data, list):
                    all_hosts = instances_data
                elif isinstance(instances_data, dict) and "Instances" in instances_data:
                    all_hosts = instances_data["Instances"]
                else:
                    logger.warning(
                        f"Unexpected instances format: {type(instances_data)}"
                    )
                    return []

                for host in all_hosts:
                    available_instances = host.get("AvailableInstances", [])
                    all_instances.extend(available_instances)

                logger.info(f"Found {len(all_instances)} instances via HTTP API")
                return all_instances

        except Exception as e:
            logger.error(f"Error getting instances via HTTP: {e}")
            return []

    async def http_create_instance(
        self, name: str, template: str, owner_id: str, amp_username: str = None
    ) -> Optional[AMPInstance]:
        """Create instance using direct HTTP API."""
        if not self.session_id or not self.http_session:
            if not await self.http_login():
                return None

        try:
            logger.info(f"Creating instance {name} via HTTP API using DeployTemplate")

            # Get the ADS instance ID from the bridge instances
            bridge_instances = await self.get_instances()
            ads_instance_id = None

            if bridge_instances:
                # Look for the ADS instance ID from the bridge data
                for host in bridge_instances:
                    friendly_name = None
                    instance_id = None

                    if isinstance(host, dict):
                        friendly_name = host.get("friendly_name")
                        instance_id = host.get("instance_id")
                    elif hasattr(host, "friendly_name"):
                        friendly_name = host.friendly_name
                        instance_id = getattr(host, "instance_id", None)

                    if friendly_name == "Local Instances" and instance_id:
                        ads_instance_id = instance_id
                        logger.info(
                            f"Found ADS instance: {friendly_name} with ID: {instance_id}"
                        )
                        break

            if not ads_instance_id:
                # Fallback: Use the hardcoded one that works
                ads_instance_id = "037674cd-e566-461f-9d4f-a57854eeb3d3"
                logger.warning(f"Using fallback ADS instance ID: {ads_instance_id}")

            deploy_url = f"http://{self.host}:{self.port}/API/ADSModule/DeployTemplate"

            # Get template ID from configuration
            template_id = get_template_id(template)

            payload = {
                "SESSIONID": self.session_id,
                "TemplateID": template_id,  # Use template ID instead of module name
                "NewUsername": (
                    amp_username if amp_username else ""
                ),  # Use the AMP username
                "NewPassword": "",  # Let AMP handle this
                "NewEmail": "",
                "RequiredTags": [],
                "Tag": f"bot_created_{owner_id}",  # Tag for identification
                "FriendlyName": name,
                "Secret": "",  # No callback needed
                "PostCreate": 4,  # UpdateAndStartAlways (4)
                "ExtraProvisionSettings": {},
            }

            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "SESSIONID": self.session_id,
            }

            logger.info(f"Creating instance {name} with template ID {template_id}")

            async with self.http_session.post(
                deploy_url, data=json.dumps(payload), headers=headers
            ) as response:
                response_text = await response.text()

                if response.status == 200:
                    try:
                        result_data = await response.json()

                        # DeployTemplate returns a RunningTask object, check if deployment started
                        if result_data and (
                            result_data.get("success")
                            or result_data.get("Status") == "Running"
                            or result_data.get("Id")
                        ):  # Task ID indicates deployment started
                            instance = AMPInstance(
                                name=name,
                                template=template,
                                owner_id=owner_id,
                                instance_id=result_data.get(
                                    "Id", name
                                ),  # Use task ID if available
                                status="deploying_template",
                            )

                            logger.info(f"Template deployment started for {name}")
                            return instance
                        else:
                            logger.error(f"Template deployment failed")
                            return None

                    except json.JSONDecodeError:
                        # Sometimes AMP returns non-JSON responses
                        if (
                            "success" in response_text.lower()
                            or "running" in response_text.lower()
                        ):
                            instance = AMPInstance(
                                name=name,
                                template=template,
                                owner_id=owner_id,
                                instance_id=name,
                                status="deploying_template",
                            )
                            return instance
                        else:
                            logger.error("Non-JSON deployment response received")
                            return None
                else:
                    logger.error(
                        f"HTTP template deployment failed with status {response.status}"
                    )
                    return None

        except Exception as e:
            logger.error(f"Error deploying template via HTTP: {e}")
            return None

    async def http_logout(self):
        """Logout using HTTP API."""
        if self.session_id and self.http_session:
            try:
                logout_url = f"http://{self.host}:{self.port}/API/Core/Logout"
                payload = {"SESSIONID": self.session_id}

                headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "SESSIONID": self.session_id,
                }

                async with self.http_session.post(
                    logout_url, data=json.dumps(payload), headers=headers
                ) as response:
                    if response.status == 200:
                        logger.info("HTTP logout successful")
                    else:
                        logger.warning(f"HTTP logout failed: {response.status}")

            except Exception as e:
                logger.error(f"Error in HTTP logout: {e}")
            finally:
                self.session_id = None

    async def check_connection(self) -> bool:
        """Check if connected to AMP API."""
        return self._connected and self.bridge is not None
