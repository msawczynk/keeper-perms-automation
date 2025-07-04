"""Keeper Commander login helper with persistent session caching.

On first run (no cached device/session), the user is prompted *interactively*
in the shell for their Keeper email, master password, and (optionally) a
two-factor code.  The resulting device token + refresh token are stored in
``%APPDATA%\\Keeper\\commander\\automation.json`` on Windows (or the equivalent
XDG path on macOS/Linux).  Subsequent runs re-use that cache – no prompts.
"""

import os
from pathlib import Path
from getpass import getpass
from keepercommander import api, params, generator      # type: ignore
from typing import List, Dict, Any, Optional

CONF_PATH = Path(
    os.getenv("KPR_CONF", r"~/.config/keeper/commander/automation.json")
).expanduser()

_sdk_cache: Optional[params.KeeperParams] = None

def _prompt_bootstrap():
    print("No cached Keeper session found – please authenticate.")
    user = input("Keeper email: ").strip()
    pwd  = getpass("Master password: ").strip()
    otp  = input("Two-factor code (leave blank if none): ").strip() or None
    return user, pwd, otp

def _login():
    kp = params.KeeperParams()  # type: ignore
    kp.config_filename = str(CONF_PATH)
    
    # Try to load cached session manually with correct field mapping
    try:
        CONF_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        # Load cached session manually
        if CONF_PATH.exists():
            import json
            with open(CONF_PATH, 'r') as f:
                config = json.load(f)
            
            # Set properties with correct field names
            if 'user' in config: kp.user = config['user']  # type: ignore
            if 'server' in config: kp.server = config['server']  # type: ignore
            if 'device_token' in config: kp.device_token = config['device_token']  # type: ignore
            if 'private_key' in config: kp.device_private_key = config['private_key']  # type: ignore
            if 'clone_code' in config: kp.clone_code = config['clone_code']  # type: ignore
            
            print(f"📁 Loaded cached session: user={config.get('user', 'unknown')}, device_token={'✓' if config.get('device_token') else '✗'}")
                    
    except Exception as e:
        print(f"Note: Could not load existing config: {e}")

    # Test existing session if we have session token
    if hasattr(kp, 'session_token') and kp.session_token:  # type: ignore
        try:
            api.sync_down(kp)  # type: ignore
            print(f"✓ Using existing session")
            return kp
        except Exception:
            print("Session expired, re-authenticating...")
    
    # Test device token if we have it
    elif hasattr(kp, 'device_token') and kp.device_token:  # type: ignore
        try:
            # Try to establish session with device token
            api.login(kp)  # type: ignore
            api.sync_down(kp)  # type: ignore
            print(f"✓ Using cached device token from {CONF_PATH}")
            return kp
        except Exception:
            print("Device token expired, requiring fresh login...")

    # interactive bootstrap unless env vars supplied
    user = os.getenv("KPR_USER")
    pwd  = os.getenv("KPR_PASS")
    otp  = os.getenv("KPR_2FA")
    if not (user and pwd):
        user, pwd, otp = _prompt_bootstrap()

    kp.user = user  # type: ignore
    kp.password = pwd  # type: ignore
    if otp:
        kp.mfa_token = otp  # type: ignore

    # Ensure config directory exists
    CONF_PATH.parent.mkdir(parents=True, exist_ok=True)

    api.login(kp)  # type: ignore
    api.sync_down(kp)  # type: ignore
    
    # Save session data manually with consistent field naming
    try:
        import json
        config_data = {
            'user': kp.user,  # type: ignore
            'server': getattr(kp, 'server', 'keepersecurity.eu'),  # type: ignore
            'device_token': getattr(kp, 'device_token', None),  # type: ignore
            'private_key': getattr(kp, 'device_private_key', None),  # type: ignore
            'clone_code': getattr(kp, 'clone_code', None),  # type: ignore
        }
        
        # Only save non-empty values
        config_data = {k: v for k, v in config_data.items() if v}
        
        with open(CONF_PATH, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        print(f"✅ Session saved: {len(config_data)} fields → {CONF_PATH}")
        
    except Exception as e:
        print(f"Warning: Could not save session cache: {e}")
    
    return kp

def get_client():
    """Public helper used by other modules."""
    global _sdk_cache
    if _sdk_cache is None:
        _sdk_cache = _login()
    return _sdk_cache

def get_teams() -> List[Dict[str, Any]]:
    """Return a list of team dictionaries from the vault."""
    sdk = get_client()
    teams: List[Dict[str, Any]] = []
    
    try:
        # Use the API to get available teams with actual names
        from keepercommander import api  # type: ignore
        rq = {'command': 'get_available_teams'}
        rs = api.communicate(sdk, rq)  # type: ignore
        
        if rs.get('result') == 'success' and 'teams' in rs:
            for team in rs['teams']:  # type: ignore
                teams.append({
                    'team_uid': team.get('team_uid', ''),
                    'team_name': team.get('team_name', f"Team {team.get('team_uid', 'Unknown')}"),
                    'team_key': team.get('team_key', None),
                })
        else:
            # Fallback: try to get teams from cache
            if hasattr(sdk, 'team_cache') and sdk.team_cache:  # type: ignore
                for team_uid, team_data in sdk.team_cache.items():  # type: ignore
                    teams.append({
                        'team_uid': team_uid,
                        'team_name': getattr(team_data, 'name', f'Team {team_uid}'),  # type: ignore
                        'team_key': getattr(team_data, 'team_key', None),  # type: ignore
                    })
    except Exception as e:
        print(f"Warning: Could not retrieve teams: {e}")
    
    return teams


def find_team_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Find a team by name."""
    for team in get_teams():
        if team.get('team_name') == name:
            return team
    return None


def get_team_uid_by_name(team_name: str) -> Optional[str]:
    """Get team UID by team name."""
    team = find_team_by_name(team_name)
    return team.get('team_uid') if team else None


def get_records() -> List[Dict[str, Any]]:
    """Get all records from the vault."""
    sdk = get_client()
    records: List[Dict[str, Any]] = []
    
    try:
        from keepercommander import api  # type: ignore
        
        if hasattr(sdk, 'record_cache') and sdk.record_cache:  # type: ignore
            for rec_uid, rec_data in sdk.record_cache.items():  # type: ignore
                try:
                    # Get the actual record with decrypted data
                    record = api.get_record(sdk, rec_uid)  # type: ignore
                    
                    # Extract record information
                    record_info = {
                        'uid': rec_uid,
                        'title': getattr(record, 'title', f'Record {rec_uid}'),
                        'folder_uid': rec_data.get('folder_uid', None),
                        'shared': rec_data.get('shared', False),
                    }
                    records.append(record_info)
                except Exception as e:
                    # Fallback to basic info if decryption fails
                    record_info = {
                        'uid': rec_uid,
                        'title': f'Record {rec_uid}',
                        'folder_uid': rec_data.get('folder_uid', None),
                        'shared': rec_data.get('shared', False),
                    }
                    records.append(record_info)
    except Exception as e:
        print(f"Warning: Could not retrieve records: {e}")
    
    return records


def get_folder_data() -> Dict[str, Any]:
    """Return comprehensive vault snapshot used by VaultService."""
    sdk = get_client()
    
    try:
        # Ensure we have the latest data
        api.sync_down(sdk)  # type: ignore
    except Exception as e:
        print(f"Warning: Could not sync vault data: {e}")
    
    folders: List[Dict[str, Any]] = []
    
    try:
        # Get folder structure from Keeper
        if hasattr(sdk, 'folder_cache') and sdk.folder_cache:  # type: ignore
            for folder_uid, folder_data in sdk.folder_cache.items():  # type: ignore
                folder_info = {
                    'uid': folder_uid,
                    'name': getattr(folder_data, 'name', f'Folder {folder_uid}'),  # type: ignore
                    'parent_uid': getattr(folder_data, 'parent_uid', None),  # type: ignore
                    'folder_type': getattr(folder_data, 'folder_type', 'user_folder'),  # type: ignore
                }
                folders.append(folder_info)
        
        # Alternative method: get shared folders
        if hasattr(sdk, 'shared_folder_cache') and sdk.shared_folder_cache:  # type: ignore
            for sf_uid, sf_data in sdk.shared_folder_cache.items():  # type: ignore
                folder_info = {
                    'uid': sf_uid,
                    'name': getattr(sf_data, 'name', f'Shared Folder {sf_uid}'),  # type: ignore
                    'parent_uid': getattr(sf_data, 'parent_uid', None),  # type: ignore
                    'folder_type': 'shared_folder',
                    'default_manage_records': getattr(sf_data, 'default_manage_records', False),  # type: ignore
                    'default_manage_users': getattr(sf_data, 'default_manage_users', False),  # type: ignore
                    'default_can_edit': getattr(sf_data, 'default_can_edit', False),  # type: ignore
                    'default_can_share': getattr(sf_data, 'default_can_share', False),  # type: ignore
                }
                folders.append(folder_info)
                
    except Exception as e:
        print(f"Warning: Could not retrieve folder data: {e}")
    
    return {
        'folders': folders,
        'records': get_records(),
        'teams': get_teams(),
    }


def create_shared_folder(name: str, parent_uid: Optional[str] = None) -> str:
    """Create a shared folder using the official FolderMakeCommand."""
    sdk = get_client()
    try:
        from keepercommander.commands.folder import FolderMakeCommand
        from keepercommander.commands.utils import SyncDownCommand
        
        cmd = FolderMakeCommand()
        sync_cmd = SyncDownCommand()
        
        # Save the current folder context
        original_current_folder = sdk.current_folder
        
        # Set the parent folder as the current folder if specified
        if parent_uid:
            sdk.current_folder = parent_uid
        
        try:
            # Determine if we should create a shared folder or a subfolder
            # based on the parent context
            if parent_uid:
                parent_folder = sdk.folder_cache.get(parent_uid)
                if parent_folder and hasattr(parent_folder, 'type'):
                    # If parent is a shared folder, create a subfolder
                    if parent_folder.type in {'shared_folder', 'shared_folder_folder'}:
                        new_folder_uid = cmd.execute(
                            params=sdk, 
                            folder=name,
                            user_folder=True  # This creates a shared_folder_folder
                        )
                    else:
                        new_folder_uid = cmd.execute(
                            params=sdk, 
                            folder=name,
                            shared_folder=True
                        )
                else:
                    # Default to shared folder if we can't determine parent type
                    new_folder_uid = cmd.execute(
                        params=sdk, 
                        folder=name,
                        shared_folder=True
                    )
            else:
                # No parent specified, create a top-level shared folder
                new_folder_uid = cmd.execute(
                    params=sdk, 
                    folder=name,
                    shared_folder=True
                )

            # Force a sync to update the local cache with the new folder
            sync_cmd.execute(sdk)

            return new_folder_uid
        finally:
            # Restore the original current folder context
            sdk.current_folder = original_current_folder

    except Exception as e:
        print(f"Error creating shared folder '{name}': {e}")
        raise e


def find_folder_by_name(name: str, parent_uid: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Find a folder by name, optionally within a specific parent folder."""
    # This is inefficient, but simple. Caching is handled by the SDK.
    folder_data = get_folder_data()
    
    for folder in folder_data.get('folders', []):
        folder_parent_uid = folder.get('parent_uid')
        # Handle root folders (parent_uid is None)
        if folder.get('name') == name and folder_parent_uid == parent_uid:
            return folder
    
    return None


def share_record_to_folder(record_uid: str, folder_uid: str) -> None:
    """Share a record to a folder using the correct move/link API."""
    sdk = get_client()
    
    try:
        from keepercommander import api  # type: ignore
        from keepercommander.subfolder import BaseFolderNode, find_folders
        
        # Get the destination folder
        dst_folder = sdk.folder_cache.get(folder_uid)
        if not dst_folder:
            raise Exception(f"Destination folder {folder_uid} not found")
        
        # Find the current folder of the record (source folder)
        src_folder = None
        folder_uids = list(find_folders(sdk, record_uid))
        if folder_uids:
            if sdk.current_folder and sdk.current_folder in folder_uids:
                src_folder = sdk.folder_cache[sdk.current_folder]
            else:
                # Check if record is in root folder
                if '' in sdk.subfolder_record_cache:
                    if record_uid in sdk.subfolder_record_cache['']:
                        src_folder = sdk.root_folder
                if not src_folder and folder_uids:
                    src_folder = sdk.folder_cache[folder_uids[0]]
        else:
            src_folder = sdk.root_folder
        
        # Prepare the move record entry
        move_entry = {
            'uid': record_uid,
            'type': 'record',
            'cascade': False
        }
        
        # Set source folder information
        if src_folder.type == BaseFolderNode.RootFolderType:
            move_entry['from_type'] = BaseFolderNode.UserFolderType
        else:
            move_entry['from_type'] = src_folder.type
            move_entry['from_uid'] = src_folder.uid
        
        # Prepare the command to link record to folder
        rq = {
            'command': 'move',
            'link': True,  # This makes it a link operation, not a move
            'move': [move_entry]
        }
        
        # Set destination folder information
        if dst_folder.type == BaseFolderNode.RootFolderType:
            rq['to_type'] = BaseFolderNode.UserFolderType
        else:
            rq['to_type'] = dst_folder.type
            rq['to_uid'] = dst_folder.uid
        
        # Calculate transition key if needed
        transition_keys = []
        transition_key = None
        rec = sdk.record_cache[record_uid]
        
        if src_folder.type in {BaseFolderNode.SharedFolderType, BaseFolderNode.SharedFolderFolderType}:
            if dst_folder.type in {BaseFolderNode.SharedFolderType, BaseFolderNode.SharedFolderFolderType}:
                ssf_uid = src_folder.uid if src_folder.type == BaseFolderNode.SharedFolderType else src_folder.shared_folder_uid
                dsf_uid = dst_folder.uid if dst_folder.type == BaseFolderNode.SharedFolderType else dst_folder.shared_folder_uid
                if ssf_uid != dsf_uid:
                    from keepercommander import crypto, utils  # type: ignore
                    shf = sdk.shared_folder_cache[dsf_uid]
                    # Use the get_transition_key logic
                    if rec.get('version', -1) >= 3:
                        tkey = crypto.encrypt_aes_v2(rec['record_key_unencrypted'], shf['shared_folder_key_unencrypted'])
                    else:
                        tkey = crypto.encrypt_aes_v1(rec['record_key_unencrypted'], shf['shared_folder_key_unencrypted'])
                    transition_key = utils.base64_url_encode(tkey)
            else:
                from keepercommander import crypto, utils  # type: ignore
                # Moving from shared to user folder
                if rec.get('version', -1) >= 3:
                    tkey = crypto.encrypt_aes_v2(rec['record_key_unencrypted'], sdk.data_key)
                else:
                    tkey = crypto.encrypt_aes_v1(rec['record_key_unencrypted'], sdk.data_key)
                transition_key = utils.base64_url_encode(tkey)
        else:
            if dst_folder.type in {BaseFolderNode.SharedFolderType, BaseFolderNode.SharedFolderFolderType}:
                from keepercommander import crypto, utils  # type: ignore
                dsf_uid = dst_folder.uid if dst_folder.type == BaseFolderNode.SharedFolderType else dst_folder.shared_folder_uid
                shf = sdk.shared_folder_cache[dsf_uid]
                # Moving from user to shared folder
                if rec.get('version', -1) >= 3:
                    tkey = crypto.encrypt_aes_v2(rec['record_key_unencrypted'], shf['shared_folder_key_unencrypted'])
                else:
                    tkey = crypto.encrypt_aes_v1(rec['record_key_unencrypted'], shf['shared_folder_key_unencrypted'])
                transition_key = utils.base64_url_encode(tkey)

        if transition_key is not None:
            transition_keys.append({
                'uid': record_uid,
                'key': transition_key
            })
        
        if transition_keys:
            rq['transition_keys'] = transition_keys
        
        # Execute the command
        rs = api.communicate(sdk, rq)  # type: ignore
        
        if rs.get('result') == 'success':
            # Sync to reflect changes
            api.sync_down(sdk)  # type: ignore
            print(f"✓ Shared record {record_uid} to folder {folder_uid}")
        else:
            raise Exception(f"Failed to share record: {rs.get('message', 'Unknown error')}")
            
    except Exception as e:
        print(f"Error sharing record {record_uid} to folder {folder_uid}: {e}")
        raise e


def add_team_to_shared_folder(team_uid: str, folder_uid: str, permissions: Dict[str, bool]) -> None:
    """Add a team to a shared folder with specific permissions."""
    sdk = get_client()
    
    try:
        from keepercommander import api  # type: ignore
        
        # Prepare the command to add team to shared folder
        rq = {
            'command': 'shared_folder_update',
            'shared_folder_uid': folder_uid,
            'add_teams': [
                {
                    'team_uid': team_uid,
                    'manage_records': permissions.get('manage_records', False),
                    'manage_users': permissions.get('manage_users', False),
                    'can_edit': permissions.get('can_edit', False),
                    'can_share': permissions.get('can_share', False)
                }
            ]
        }
        
        # Execute the command
        rs = api.communicate(sdk, rq)  # type: ignore
        
        if rs.get('result') == 'success':
            # Sync to reflect changes
            api.sync_down(sdk)  # type: ignore
            print(f"✓ Added team {team_uid} to shared folder {folder_uid}")
        else:
            raise Exception(f"Failed to add team to shared folder: {rs.get('message', 'Unknown error')}")
            
    except Exception as e:
        print(f"Error adding team {team_uid} to shared folder {folder_uid}: {e}")


def get_record(record_uid: str) -> Optional[Any]:
    """Get a specific record by UID."""
    sdk = get_client()
    
    try:
        if hasattr(sdk, 'record_cache') and sdk.record_cache:  # type: ignore
            return sdk.record_cache.get(record_uid)  # type: ignore
    except Exception as e:
        print(f"Warning: Could not retrieve record {record_uid}: {e}")
    
    return None


def ensure_team_folder_path(team_name: str, folder_path: str, root_folder_name: str = "[Perms]") -> Optional[str]:
    """
    Ensures a team-specific folder path exists by creating the structure:
    [Perms] (private) -> TeamName (shared) -> folder_path (private subfolders)
    
    Returns the UID of the final folder in the team's path.
    """
    sdk = get_client()
    
    try:
        # 1. Ensure root folder exists (private)
        root_folder = find_folder_by_name(root_folder_name, parent_uid=None)
        if not root_folder:
            from keepercommander.commands.folder import FolderMakeCommand
            cmd = FolderMakeCommand()
            root_folder_uid = cmd.execute(
                params=sdk,
                folder=root_folder_name,
                user_folder=True
            )
            print(f"✓ Created root user folder: {root_folder_name}")
        else:
            root_folder_uid = root_folder.get('uid')
            print(f"✓ Found existing folder: {root_folder_name}")
        
        # 2. Ensure team shared folder exists under root
        team_folder = find_folder_by_name(team_name, parent_uid=root_folder_uid)
        if not team_folder:
            team_folder_uid = create_shared_folder(team_name, parent_uid=root_folder_uid)
            print(f"✓ Created team shared folder: {team_name}")
        else:
            team_folder_uid = team_folder.get('uid')
            print(f"✓ Found existing team folder: {team_name}")
        
        # 3. Create the folder path under the team's shared folder
        # All folders under the team folder are private subfolders
        path_components = [c.strip() for c in folder_path.split('/') if c.strip()]
        current_parent_uid = team_folder_uid
        
        for component in path_components:
            existing_folder = find_folder_by_name(component, parent_uid=current_parent_uid)
            
            if existing_folder:
                current_parent_uid = existing_folder.get('uid')
                print(f"✓ Found existing folder: {component}")
            else:
                # Create as private subfolder within the shared team folder
                from keepercommander.commands.folder import FolderMakeCommand
                cmd = FolderMakeCommand()
                
                # Set current folder context to the parent
                original_current_folder = sdk.current_folder
                sdk.current_folder = current_parent_uid
                
                try:
                    current_parent_uid = cmd.execute(
                        params=sdk,
                        folder=component,
                        user_folder=True  # Private subfolder within shared folder
                    )
                    # Force sync to update folder cache
                    from keepercommander.commands.utils import SyncDownCommand
                    sync_cmd = SyncDownCommand()
                    sync_cmd.execute(sdk)
                    print(f"✓ Created private subfolder: {component}")
                finally:
                    # Restore original context
                    sdk.current_folder = original_current_folder
        
        return current_parent_uid
        
    except Exception as e:
        print(f"❌ Error ensuring team folder path '{team_name}/{folder_path}': {e}")
        return None


# Old ensure_folder_path function removed - replaced with ensure_team_folder_path
# for per-team folder structure implementation

def create_record(record_data: Dict[str, Any], folder_uid: Optional[str] = None) -> str:
    """Create a new record in the vault."""
    sdk = get_client()
    
    try:
        from keepercommander import api, vault, record_management  # type: ignore
        from keepercommander.subfolder import find_folders
        
        # Create a new record
        record = vault.KeeperRecord.create(sdk, 'login')
        record.title = record_data.get('title', 'Untitled Record')
        
        # Add custom fields from record_data
        if 'fields' in record_data:
            for field_data in record_data['fields']:
                field_type = field_data.get('type', 'text')
                field_label = field_data.get('label', '')
                field_value = field_data.get('value', '')
                
                if field_type == 'multiline':
                    field = vault.TypedField.new_field('multiline', field_value, field_label)
                elif field_type == 'text':
                    field = vault.TypedField.new_field('text', field_value, field_label)
                else:
                    field = vault.TypedField.new_field('text', field_value, field_label)
                
                record.fields.append(field)
        
        # Add the record to the vault
        record_management.add_record_to_folder(sdk, record, folder_uid)
        
        # Force sync to update cache
        api.sync_down(sdk)
        
        return record.record_uid
        
    except Exception as e:
        print(f"Error creating record: {e}")
        raise e


def update_record(record_uid: str, record_data: Dict[str, Any]) -> None:
    """Update an existing record in the vault."""
    sdk = get_client()
    
    try:
        from keepercommander import api, vault  # type: ignore
        
        # Get the existing record
        record = get_record(record_uid)
        if not record:
            raise Exception(f"Record {record_uid} not found")
        
        # Update the title if provided
        if 'title' in record_data:
            record.title = record_data['title']
        
        # Update fields if provided
        if 'fields' in record_data:
            # Clear existing custom fields
            record.fields = [f for f in record.fields if f.type in ('login', 'password', 'url')]
            
            # Add new fields
            for field_data in record_data['fields']:
                field_type = field_data.get('type', 'text')
                field_label = field_data.get('label', '')
                field_value = field_data.get('value', '')
                
                if field_type == 'multiline':
                    field = vault.TypedField.new_field('multiline', field_value, field_label)
                elif field_type == 'text':
                    field = vault.TypedField.new_field('text', field_value, field_label)
                else:
                    field = vault.TypedField.new_field('text', field_value, field_label)
                
                record.fields.append(field)
        
        # Update the record
        record_management.update_record(sdk, record)
        
        # Force sync to update cache
        api.sync_down(sdk)
        
    except Exception as e:
        print(f"Error updating record {record_uid}: {e}")
        raise e


def find_records_by_title(title: str) -> List[Dict[str, Any]]:
    """Find records by title."""
    sdk = get_client()
    
    try:
        # Ensure we have the latest data
        from keepercommander import api  # type: ignore
        api.sync_down(sdk)
        
        matching_records = []
        
        # Search through all records
        if hasattr(sdk, 'record_cache') and sdk.record_cache:
            for record_uid, record_data in sdk.record_cache.items():
                if hasattr(record_data, 'title') and record_data.title == title:
                    matching_records.append({
                        'record_uid': record_uid,
                        'title': record_data.title
                    })
        
        return matching_records
        
    except Exception as e:
        print(f"Error finding records by title '{title}': {e}")
        return []


def ensure_folder_path(folder_path: str) -> str:
    """Ensure a folder path exists and return the folder UID."""
    sdk = get_client()
    
    try:
        from keepercommander.commands.folder import FolderMakeCommand
        from keepercommander import api  # type: ignore
        
        # Split the path into components
        path_parts = [part.strip() for part in folder_path.split('/') if part.strip()]
        
        if not path_parts:
            raise Exception("Empty folder path")
        
        current_folder_uid = None
        
        # Create each folder in the path
        for i, folder_name in enumerate(path_parts):
            # Check if folder already exists
            existing_folder = find_folder_by_name(folder_name, current_folder_uid)
            
            if existing_folder:
                current_folder_uid = existing_folder['uid']
            else:
                # Create the folder
                if i == 0:
                    # First folder - create as user folder
                    current_folder_uid = create_shared_folder(folder_name, current_folder_uid)
                else:
                    # Subsequent folders - create as subfolders
                    current_folder_uid = create_shared_folder(folder_name, current_folder_uid)
        
        return current_folder_uid
        
    except Exception as e:
        print(f"Error ensuring folder path '{folder_path}': {e}")
        raise e
