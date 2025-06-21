"""
Service Registry Module

This module provides comprehensive service registry capabilities with registration,
deduplication, persistence, and querying functionality for discovered services.
"""

import logging
import json
import asyncio
import os
import sqlite3
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import uuid
from pathlib import Path
import threading
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


@dataclass
class RegisteredService:
    """Data class representing a registered service"""
    id: str
    name: str
    type: str
    status: str
    location: str
    metadata: Dict[str, Any]
    endpoints: List[Dict[str, Any]]
    health_status: Optional[str] = None
    tags: Optional[List[str]] = None
    dependencies: Optional[List[str]] = None
    registered_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_seen: Optional[str] = None
    version: Optional[str] = None
    owner: Optional[str] = None
    source: Optional[str] = None

    def __post_init__(self):
        if self.registered_at is None:
            self.registered_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = self.registered_at
        if self.last_seen is None:
            self.last_seen = self.registered_at
        if self.tags is None:
            self.tags = []
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class RegistrationResult:
    """Data class representing service registration result"""
    success: bool
    service_id: str
    message: str
    action: str  # 'created', 'updated', 'duplicate', 'error'
    existing_service: Optional[RegisteredService] = None


class ServiceRegistry:
    """
    Comprehensive service registry that manages service registration,
    deduplication, persistence, and querying with SQLite backend.
    """

    def __init__(self, storage_path: str = './service_registry.db',
                 enable_persistence: bool = True,
                 enable_deduplication: bool = True,
                 max_service_age_days: int = 30):
        """
        Initialize the service registry.

        Args:
            storage_path: Path to SQLite database file
            enable_persistence: Whether to persist services to disk
            enable_deduplication: Whether to deduplicate services
            max_service_age_days: Maximum age for services before cleanup
        """
        self.storage_path = storage_path
        self.enable_persistence = enable_persistence
        self.enable_deduplication = enable_deduplication
        self.max_service_age_days = max_service_age_days

        # In-memory service cache
        self.services: Dict[str, RegisteredService] = {}
        self.service_index: Dict[str, Set[str]] = {
            'by_name': {},
            'by_type': {},
            'by_status': {},
            'by_tag': {},
            'by_owner': {},
            'by_source': {}
        }

        # Thread lock for thread safety
        self.lock = threading.RLock()

        # Initialize database
        if self.enable_persistence:
            self._init_database()
            self._load_services_from_db()

    def _init_database(self):
        """Initialize SQLite database with required tables"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(self.storage_path)), exist_ok=True)

            with sqlite3.connect(self.storage_path) as conn:
                cursor = conn.cursor()

                # Create services table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS services (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        type TEXT NOT NULL,
                        status TEXT NOT NULL,
                        location TEXT,
                        metadata TEXT,
                        endpoints TEXT,
                        health_status TEXT,
                        tags TEXT,
                        dependencies TEXT,
                        registered_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        last_seen TEXT NOT NULL,
                        version TEXT,
                        owner TEXT,
                        source TEXT
                    )
                ''')

                # Create indexes for faster queries
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_service_name ON services(name)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_service_type ON services(type)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_service_status ON services(status)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_service_owner ON services(owner)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_service_source ON services(source)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_service_updated ON services(updated_at)')

                # Create service history table for tracking changes
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS service_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        service_id TEXT NOT NULL,
                        action TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        changes TEXT,
                        FOREIGN KEY (service_id) REFERENCES services (id)
                    )
                ''')

                conn.commit()
                logger.info(f"Initialized service registry database at {self.storage_path}")

        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise

    def _load_services_from_db(self):
        """Load services from database into memory cache"""
        try:
            with sqlite3.connect(self.storage_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM services')

                for row in cursor.fetchall():
                    service = self._row_to_service(row)
                    self.services[service.id] = service
                    self._update_indexes(service)

                logger.info(f"Loaded {len(self.services)} services from database")

        except Exception as e:
            logger.error(f"Error loading services from database: {e}")

    def _row_to_service(self, row: tuple) -> RegisteredService:
        """Convert database row to RegisteredService object"""
        return RegisteredService(
            id=row[0],
            name=row[1],
            type=row[2],
            status=row[3],
            location=row[4],
            metadata=json.loads(row[5]) if row[5] else {},
            endpoints=json.loads(row[6]) if row[6] else [],
            health_status=row[7],
            tags=json.loads(row[8]) if row[8] else [],
            dependencies=json.loads(row[9]) if row[9] else [],
            registered_at=row[10],
            updated_at=row[11],
            last_seen=row[12],
            version=row[13],
            owner=row[14],
            source=row[15]
        )

    def _service_to_row(self, service: RegisteredService) -> tuple:
        """Convert RegisteredService object to database row"""
        return (
            service.id,
            service.name,
            service.type,
            service.status,
            service.location,
            json.dumps(service.metadata),
            json.dumps(service.endpoints),
            service.health_status,
            json.dumps(service.tags),
            json.dumps(service.dependencies),
            service.registered_at,
            service.updated_at,
            service.last_seen,
            service.version,
            service.owner,
            service.source
        )

    def register_service(self, service_data: Dict[str, Any]) -> RegistrationResult:
        """
        Register a new service or update existing one.

        Args:
            service_data: Service information dictionary

        Returns:
            RegistrationResult with registration details
        """
        with self.lock:
            try:
                # Generate service ID if not provided
                service_id = service_data.get('id') or str(uuid.uuid4())

                # Check for existing service
                existing_service = None
                if self.enable_deduplication:
                    existing_service = self._find_duplicate_service(service_data)

                if existing_service:
                    # Update existing service
                    updated_service = self._merge_service_data(existing_service, service_data)
                    updated_service.updated_at = datetime.now().isoformat()
                    updated_service.last_seen = updated_service.updated_at

                    self.services[existing_service.id] = updated_service
                    self._update_indexes(updated_service)

                    if self.enable_persistence:
                        self._save_service_to_db(updated_service)
                        self._log_service_history(existing_service.id, 'updated', service_data)

                    return RegistrationResult(
                        success=True,
                        service_id=existing_service.id,
                        message=f"Updated existing service: {existing_service.name}",
                        action='updated',
                        existing_service=existing_service
                    )

                else:
                    # Create new service
                    new_service = RegisteredService(
                        id=service_id,
                        name=service_data.get('name', 'unknown'),
                        type=service_data.get('type', 'unknown'),
                        status=service_data.get('status', 'active'),
                        location=service_data.get('location', ''),
                        metadata=service_data.get('metadata', {}),
                        endpoints=service_data.get('endpoints', []),
                        health_status=service_data.get('health_status'),
                        tags=service_data.get('tags', []),
                        dependencies=service_data.get('dependencies', []),
                        version=service_data.get('version'),
                        owner=service_data.get('owner'),
                        source=service_data.get('source', 'discovery')
                    )

                    self.services[service_id] = new_service
                    self._update_indexes(new_service)

                    if self.enable_persistence:
                        self._save_service_to_db(new_service)
                        self._log_service_history(service_id, 'created', service_data)

                    return RegistrationResult(
                        success=True,
                        service_id=service_id,
                        message=f"Registered new service: {new_service.name}",
                        action='created'
                    )

            except Exception as e:
                logger.error(f"Error registering service: {e}")
                return RegistrationResult(
                    success=False,
                    service_id=service_data.get('id', 'unknown'),
                    message=f"Registration failed: {str(e)}",
                    action='error'
                )

    def _find_duplicate_service(self, service_data: Dict[str, Any]) -> Optional[RegisteredService]:
        """Find duplicate service based on name, type, and location"""
        name = service_data.get('name')
        service_type = service_data.get('type')
        location = service_data.get('location')

        for service in self.services.values():
            if (service.name == name and
                service.type == service_type and
                service.location == location):
                return service

        return None

    def _merge_service_data(self, existing: RegisteredService,
                           new_data: Dict[str, Any]) -> RegisteredService:
        """Merge new service data with existing service"""
        # Create a copy of existing service
        merged = RegisteredService(**asdict(existing))

        # Update with new data
        for key, value in new_data.items():
            if hasattr(merged, key) and value is not None:
                if key == 'metadata':
                    # Merge metadata dictionaries
                    merged.metadata = {**merged.metadata, **value}
                elif key == 'tags':
                    # Merge tags lists
                    merged.tags = list(set(merged.tags + value))
                elif key == 'endpoints':
                    # Replace endpoints
                    merged.endpoints = value
                else:
                    setattr(merged, key, value)

        return merged

    def _update_indexes(self, service: RegisteredService):
        """Update service indexes for fast querying"""
        service_id = service.id

        # Update name index
        if service.name not in self.service_index['by_name']:
            self.service_index['by_name'][service.name] = set()
        self.service_index['by_name'][service.name].add(service_id)

        # Update type index
        if service.type not in self.service_index['by_type']:
            self.service_index['by_type'][service.type] = set()
        self.service_index['by_type'][service.type].add(service_id)

        # Update status index
        if service.status not in self.service_index['by_status']:
            self.service_index['by_status'][service.status] = set()
        self.service_index['by_status'][service.status].add(service_id)

        # Update tag indexes
        for tag in service.tags:
            if tag not in self.service_index['by_tag']:
                self.service_index['by_tag'][tag] = set()
            self.service_index['by_tag'][tag].add(service_id)

        # Update owner index
        if service.owner:
            if service.owner not in self.service_index['by_owner']:
                self.service_index['by_owner'][service.owner] = set()
            self.service_index['by_owner'][service.owner].add(service_id)

        # Update source index
        if service.source:
            if service.source not in self.service_index['by_source']:
                self.service_index['by_source'][service.source] = set()
            self.service_index['by_source'][service.source].add(service_id)

    def _save_service_to_db(self, service: RegisteredService):
        """Save service to database"""
        try:
            with sqlite3.connect(self.storage_path) as conn:
                cursor = conn.cursor()
                row = self._service_to_row(service)

                cursor.execute('''
                    INSERT OR REPLACE INTO services VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', row)

                conn.commit()

        except Exception as e:
            logger.error(f"Error saving service to database: {e}")

    def _log_service_history(self, service_id: str, action: str,
                           changes: Dict[str, Any]):
        """Log service change history"""
        if not self.enable_persistence:
            return

        try:
            with sqlite3.connect(self.storage_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO service_history (service_id, action, timestamp, changes)
                    VALUES (?, ?, ?, ?)
                ''', (
                    service_id,
                    action,
                    datetime.now().isoformat(),
                    json.dumps(changes)
                ))
                conn.commit()

        except Exception as e:
            logger.error(f"Error logging service history: {e}")

    def deregister_service(self, service_id: str) -> bool:
        """
        Deregister a service from the registry.

        Args:
            service_id: ID of service to deregister

        Returns:
            True if service was deregistered, False otherwise
        """
        with self.lock:
            try:
                if service_id not in self.services:
                    return False

                service = self.services[service_id]

                # Remove from indexes
                self._remove_from_indexes(service)

                # Remove from memory
                del self.services[service_id]

                # Remove from database
                if self.enable_persistence:
                    with sqlite3.connect(self.storage_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute('DELETE FROM services WHERE id = ?', (service_id,))
                        conn.commit()

                    self._log_service_history(service_id, 'deregistered', {})

                logger.info(f"Deregistered service: {service.name} ({service_id})")
                return True

            except Exception as e:
                logger.error(f"Error deregistering service {service_id}: {e}")
                return False

    def _remove_from_indexes(self, service: RegisteredService):
        """Remove service from all indexes"""
        service_id = service.id

        # Remove from name index
        if service.name in self.service_index['by_name']:
            self.service_index['by_name'][service.name].discard(service_id)
            if not self.service_index['by_name'][service.name]:
                del self.service_index['by_name'][service.name]

        # Remove from type index
        if service.type in self.service_index['by_type']:
            self.service_index['by_type'][service.type].discard(service_id)
            if not self.service_index['by_type'][service.type]:
                del self.service_index['by_type'][service.type]

        # Remove from status index
        if service.status in self.service_index['by_status']:
            self.service_index['by_status'][service.status].discard(service_id)
            if not self.service_index['by_status'][service.status]:
                del self.service_index['by_status'][service.status]

        # Remove from tag indexes
        for tag in service.tags:
            if tag in self.service_index['by_tag']:
                self.service_index['by_tag'][tag].discard(service_id)
                if not self.service_index['by_tag'][tag]:
                    del self.service_index['by_tag'][tag]

        # Remove from owner index
        if service.owner and service.owner in self.service_index['by_owner']:
            self.service_index['by_owner'][service.owner].discard(service_id)
            if not self.service_index['by_owner'][service.owner]:
                del self.service_index['by_owner'][service.owner]

        # Remove from source index
        if service.source and service.source in self.service_index['by_source']:
            self.service_index['by_source'][service.source].discard(service_id)
            if not self.service_index['by_source'][service.source]:
                del self.service_index['by_source'][service.source]

    def get_service(self, service_id: str) -> Optional[RegisteredService]:
        """Get service by ID"""
        return self.services.get(service_id)

    def list_services(self, filters: Optional[Dict[str, Any]] = None,
                     limit: Optional[int] = None,
                     offset: int = 0) -> List[RegisteredService]:
        """
        List services with optional filtering.

        Args:
            filters: Dictionary of filters to apply
            limit: Maximum number of services to return
            offset: Number of services to skip

        Returns:
            List of matching services
        """
        with self.lock:
            if not filters:
                services = list(self.services.values())
            else:
                services = self._filter_services(filters)

            # Apply pagination
            if offset > 0:
                services = services[offset:]
            if limit is not None:
                services = services[:limit]

            return services

    def _filter_services(self, filters: Dict[str, Any]) -> List[RegisteredService]:
        """Filter services based on criteria"""
        matching_ids = None

        for key, value in filters.items():
            if key == 'name':
                ids = self.service_index['by_name'].get(value, set())
            elif key == 'type':
                ids = self.service_index['by_type'].get(value, set())
            elif key == 'status':
                ids = self.service_index['by_status'].get(value, set())
            elif key == 'tag':
                ids = self.service_index['by_tag'].get(value, set())
            elif key == 'owner':
                ids = self.service_index['by_owner'].get(value, set())
            elif key == 'source':
                ids = self.service_index['by_source'].get(value, set())
            elif key == 'tags':
                # Multiple tags (intersection)
                ids = None
                for tag in value:
                    tag_ids = self.service_index['by_tag'].get(tag, set())
                    ids = tag_ids if ids is None else ids.intersection(tag_ids)
                ids = ids or set()
            else:
                # Custom filter - check service attributes
                ids = set()
                for service_id, service in self.services.items():
                    if hasattr(service, key) and getattr(service, key) == value:
                        ids.add(service_id)

            # Intersect with previous results
            if matching_ids is None:
                matching_ids = ids
            else:
                matching_ids = matching_ids.intersection(ids)

        if matching_ids is None:
            return []

        return [self.services[service_id] for service_id in matching_ids
                if service_id in self.services]

    def search_services(self, query: str) -> List[RegisteredService]:
        """
        Search services by name, type, or tags.

        Args:
            query: Search query string

        Returns:
            List of matching services
        """
        query_lower = query.lower()
        matching_services = []

        for service in self.services.values():
            # Check name
            if query_lower in service.name.lower():
                matching_services.append(service)
                continue

            # Check type
            if query_lower in service.type.lower():
                matching_services.append(service)
                continue

            # Check tags
            if any(query_lower in tag.lower() for tag in service.tags):
                matching_services.append(service)
                continue

            # Check metadata
            metadata_str = json.dumps(service.metadata).lower()
            if query_lower in metadata_str:
                matching_services.append(service)

        return matching_services

    def update_service_status(self, service_id: str, status: str) -> bool:
        """Update service status"""
        with self.lock:
            if service_id not in self.services:
                return False

            service = self.services[service_id]
            old_status = service.status

            service.status = status
            service.updated_at = datetime.now().isoformat()
            service.last_seen = service.updated_at

            # Update indexes
            self._update_indexes(service)

            # Save to database
            if self.enable_persistence:
                self._save_service_to_db(service)
                self._log_service_history(service_id, 'status_updated', {
                    'old_status': old_status,
                    'new_status': status
                })

            return True

    def update_service_health(self, service_id: str, health_status: str) -> bool:
        """Update service health status"""
        with self.lock:
            if service_id not in self.services:
                return False

            service = self.services[service_id]
            old_health = service.health_status

            service.health_status = health_status
            service.updated_at = datetime.now().isoformat()
            service.last_seen = service.updated_at

            # Save to database
            if self.enable_persistence:
                self._save_service_to_db(service)
                self._log_service_history(service_id, 'health_updated', {
                    'old_health': old_health,
                    'new_health': health_status
                })

            return True

    def cleanup_stale_services(self) -> int:
        """
        Remove services that haven't been seen recently.

        Returns:
            Number of services removed
        """
        cutoff_date = datetime.now() - timedelta(days=self.max_service_age_days)
        cutoff_str = cutoff_date.isoformat()

        stale_services = []
        for service in self.services.values():
            if service.last_seen < cutoff_str:
                stale_services.append(service.id)

        for service_id in stale_services:
            self.deregister_service(service_id)

        if stale_services:
            logger.info(f"Cleaned up {len(stale_services)} stale services")

        return len(stale_services)

    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        with self.lock:
            stats = {
                'total_services': len(self.services),
                'services_by_type': {},
                'services_by_status': {},
                'services_by_health': {},
                'services_by_source': {},
                'oldest_service': None,
                'newest_service': None,
                'registry_size_mb': 0.0
            }

            if not self.services:
                return stats

            # Calculate statistics
            for service in self.services.values():
                # By type
                service_type = service.type
                stats['services_by_type'][service_type] = \
                    stats['services_by_type'].get(service_type, 0) + 1

                # By status
                status = service.status
                stats['services_by_status'][status] = \
                    stats['services_by_status'].get(status, 0) + 1

                # By health
                health = service.health_status or 'unknown'
                stats['services_by_health'][health] = \
                    stats['services_by_health'].get(health, 0) + 1

                # By source
                source = service.source or 'unknown'
                stats['services_by_source'][source] = \
                    stats['services_by_source'].get(source, 0) + 1

            # Find oldest and newest services
            services_by_date = sorted(self.services.values(),
                                    key=lambda s: s.registered_at)
            stats['oldest_service'] = {
                'id': services_by_date[0].id,
                'name': services_by_date[0].name,
                'registered_at': services_by_date[0].registered_at
            }
            stats['newest_service'] = {
                'id': services_by_date[-1].id,
                'name': services_by_date[-1].name,
                'registered_at': services_by_date[-1].registered_at
            }

            # Calculate registry size
            if self.enable_persistence and os.path.exists(self.storage_path):
                stats['registry_size_mb'] = os.path.getsize(self.storage_path) / (1024 * 1024)

            return stats

    def export_services(self, format: str = 'json') -> str:
        """
        Export services in specified format.

        Args:
            format: Export format ('json', 'csv')

        Returns:
            Exported data as string
        """
        with self.lock:
            if format.lower() == 'json':
                services_data = [asdict(service) for service in self.services.values()]
                return json.dumps(services_data, indent=2)

            elif format.lower() == 'csv':
                import csv
                import io

                output = io.StringIO()
                if not self.services:
                    return ""

                # Get field names from first service
                fieldnames = list(asdict(list(self.services.values())[0]).keys())
                writer = csv.DictWriter(output, fieldnames=fieldnames)

                writer.writeheader()
                for service in self.services.values():
                    row = asdict(service)
                    # Convert lists and dicts to JSON strings for CSV
                    for key, value in row.items():
                        if isinstance(value, (list, dict)):
                            row[key] = json.dumps(value)
                    writer.writerow(row)

                return output.getvalue()

            else:
                raise ValueError(f"Unsupported export format: {format}")

    def import_services(self, data: str, format: str = 'json') -> int:
        """
        Import services from data string.

        Args:
            data: Data to import
            format: Data format ('json', 'csv')

        Returns:
            Number of services imported
        """
        imported_count = 0

        try:
            if format.lower() == 'json':
                services_data = json.loads(data)
                for service_data in services_data:
                    result = self.register_service(service_data)
                    if result.success:
                        imported_count += 1

            elif format.lower() == 'csv':
                import csv
                import io

                reader = csv.DictReader(io.StringIO(data))
                for row in reader:
                    # Convert JSON strings back to objects
                    for key, value in row.items():
                        if key in ['metadata', 'endpoints', 'tags', 'dependencies']:
                            try:
                                row[key] = json.loads(value) if value else []
                            except json.JSONDecodeError:
                                row[key] = []

                    result = self.register_service(row)
                    if result.success:
                        imported_count += 1

            else:
                raise ValueError(f"Unsupported import format: {format}")

            logger.info(f"Imported {imported_count} services")

        except Exception as e:
            logger.error(f"Error importing services: {e}")

        return imported_count

    def close(self):
        """Close registry and cleanup resources"""
        with self.lock:
            logger.info("Closing service registry")
            # Any cleanup operations would go here
