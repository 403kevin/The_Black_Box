"""
config_loader.py

Loads and validates the CONFIG_MASTER_V6.0.1.yaml configuration file.
Provides singleton access to config throughout the application.
Handles environment variable substitution for API keys.

Location: The_Black_Box/config/config_loader.py
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigLoader:
    """
    Singleton configuration loader for SentimentSignal v6.1.
    
    Loads YAML config once, validates structure, and provides
    easy access to nested configuration values throughout the codebase.
    """
    
    _instance: Optional['ConfigLoader'] = None
    _config: Optional[Dict[str, Any]] = None
    
    def __new__(cls):
        """Singleton pattern - only one instance exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize config loader (only runs once due to singleton)."""
        if self._config is None:
            self._load_config()
    
    def _load_config(self) -> None:
        """Load and validate the YAML configuration file."""
        # Determine config file path (relative to this file)
        config_dir = Path(__file__).parent
        config_file = config_dir / "CONFIG_MASTER_V6.0.1.yaml"
        
        if not config_file.exists():
            raise FileNotFoundError(
                f"Config file not found: {config_file}\n"
                f"Expected location: The_Black_Box/config/CONFIG_MASTER_V6.0.1.yaml"
            )
        
        # Load YAML
        with open(config_file, 'r') as f:
            self._config = yaml.safe_load(f)
        
        # Substitute environment variables for API keys
        self._substitute_env_vars()
        
        # Validate required top-level sections exist
        self._validate_config()
        
        print(f"✅ Config loaded successfully from: {config_file}")
        print(f"   Version: {self._config.get('system', {}).get('version', 'Unknown')}")
        print(f"   Phase: {self._config.get('system', {}).get('current_phase', 'Unknown')}")
    
    def _substitute_env_vars(self) -> None:
        """
        Replace placeholder strings like 'ENV:API_KEY' with actual environment variables.
        This allows sensitive keys to be stored in environment rather than committed to git.
        """
        def replace_env(obj: Any) -> Any:
            """Recursively replace ENV:VAR_NAME with os.environ['VAR_NAME']."""
            if isinstance(obj, dict):
                return {k: replace_env(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_env(item) for item in obj]
            elif isinstance(obj, str) and obj.startswith('ENV:'):
                env_var = obj[4:]  # Remove 'ENV:' prefix
                value = os.environ.get(env_var)
                if value is None:
                    print(f"⚠️  Warning: Environment variable '{env_var}' not found, using placeholder")
                    return obj  # Keep placeholder if env var not set
                return value
            else:
                return obj
        
        self._config = replace_env(self._config)
    
    def _validate_config(self) -> None:
        """Validate that required configuration sections exist."""
        required_sections = [
            'system',
            'station_1_radar',
            'station_2_prescreen',
            'station_3_scoring',
            'station_4_sizing',
            'station_5_execution',
            'station_6_exits',
            'logging',
            'performance_targets'
        ]
        
        missing = [section for section in required_sections if section not in self._config]
        
        if missing:
            raise ValueError(
                f"Config validation failed. Missing required sections: {missing}\n"
                f"Please check CONFIG_MASTER_V6.0.1.yaml"
            )
    
    def get(self, *keys: str, default: Any = None) -> Any:
        """
        Get nested configuration value using dot notation.
        
        Args:
            *keys: Sequence of keys to traverse (e.g., 'system', 'version')
            default: Default value if key path doesn't exist
        
        Returns:
            Configuration value at the specified path, or default if not found
        
        Examples:
            >>> config = ConfigLoader()
            >>> config.get('system', 'version')
            '6.0.1'
            >>> config.get('station_1_radar', 'enabled')
            False
            >>> config.get('station_3_scoring', 'sentiment_layer', 'finbert', 'enabled')
            False
        """
        value = self._config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def get_station_config(self, station_num: int) -> Dict[str, Any]:
        """
        Get complete configuration for a specific station.
        
        Args:
            station_num: Station number (1-6)
        
        Returns:
            Dictionary containing all station configuration
        
        Example:
            >>> config = ConfigLoader()
            >>> radar_config = config.get_station_config(1)
            >>> print(radar_config['enabled'])
            False
        """
        station_key = f'station_{station_num}_'
        station_map = {
            1: 'radar',
            2: 'prescreen',
            3: 'scoring',
            4: 'sizing',
            5: 'execution',
            6: 'exits'
        }
        
        if station_num not in station_map:
            raise ValueError(f"Invalid station number: {station_num}. Must be 1-6.")
        
        config_key = f"{station_key}{station_map[station_num]}"
        return self.get(config_key, default={})
    
    def is_station_enabled(self, station_num: int) -> bool:
        """
        Check if a station is enabled.
        
        Args:
            station_num: Station number (1-6)
        
        Returns:
            True if station is enabled, False otherwise
        
        Example:
            >>> config = ConfigLoader()
            >>> config.is_station_enabled(1)
            False
        """
        station_config = self.get_station_config(station_num)
        return station_config.get('enabled', False)
    
    def is_edge_enabled(self, edge_name: str) -> bool:
        """
        Check if a specific edge feature is enabled.
        
        Args:
            edge_name: Name of edge feature (e.g., 'whale_tracking', 'sarcasm_detection')
        
        Returns:
            True if edge feature is enabled, False otherwise
        
        Example:
            >>> config = ConfigLoader()
            >>> config.is_edge_enabled('whale_tracking')
            False
        """
        # Edge features can be in multiple locations
        # Check Station 1 edge features
        radar_edges = self.get('station_1_radar', 'edge_features', default={})
        if edge_name in radar_edges:
            return radar_edges[edge_name].get('enabled', False)
        
        # Check Station 3 edge features
        scoring_edges = self.get('station_3_scoring', 'edge_enhancements', default={})
        if edge_name in scoring_edges:
            return scoring_edges[edge_name].get('enabled', False)
        
        # Check Station 6 edge features
        exit_edges = self.get('station_6_exits', 'edge_features', default={})
        if edge_name in exit_edges:
            return exit_edges[edge_name].get('enabled', False)
        
        # Check v6.1 behavioral edges
        behavioral_edges = self.get('behavioral_edges', default={})
        if edge_name in behavioral_edges:
            return behavioral_edges[edge_name].get('enabled', False)
        
        # Check v6.1 risk management
        risk_mgmt = self.get('risk_management', default={})
        if edge_name in risk_mgmt:
            return risk_mgmt[edge_name].get('enabled', False)
        
        return False
    
    def get_api_key(self, service: str) -> Optional[str]:
        """
        Get API key for a specific service.
        
        Args:
            service: Service name ('reddit', 'stocktwits', 'ibkr', etc.)
        
        Returns:
            API key string if found, None otherwise
        
        Example:
            >>> config = ConfigLoader()
            >>> reddit_key = config.get_api_key('reddit')
        """
        api_keys = self.get('system', 'api_keys', default={})
        return api_keys.get(service)
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get complete logging configuration."""
        return self.get('logging', default={})
    
    def get_performance_targets(self, phase: Optional[int] = None) -> Dict[str, Any]:
        """
        Get performance targets for a specific phase or current phase.
        
        Args:
            phase: Phase number (0-7), or None for current phase
        
        Returns:
            Dictionary with win_rate, avg_profit, monthly_profit targets
        """
        if phase is None:
            phase = self.get('system', 'current_phase', default=0)
        
        targets = self.get('performance_targets', default={})
        phase_key = f'phase_{phase}'
        
        return targets.get(phase_key, {})
    
    def reload(self) -> None:
        """
        Reload configuration from file.
        Useful for development/testing when config changes.
        """
        self._config = None
        self._load_config()
        print("🔄 Config reloaded")
    
    @property
    def raw_config(self) -> Dict[str, Any]:
        """
        Get raw configuration dictionary.
        Use sparingly - prefer typed getter methods.
        """
        return self._config.copy()


# Convenience function for quick access
def get_config() -> ConfigLoader:
    """
    Get the singleton ConfigLoader instance.
    
    Returns:
        ConfigLoader instance
    
    Example:
        >>> from config.config_loader import get_config
        >>> config = get_config()
        >>> version = config.get('system', 'version')
    """
    return ConfigLoader()


# Module-level testing
if __name__ == '__main__':
    """
    Test the config loader.
    Run: python -m config.config_loader
    """
    print("=" * 60)
    print("CONFIG LOADER TEST")
    print("=" * 60)
    
    try:
        config = get_config()
        
        # Test basic access
        print("\n1. System Info:")
        print(f"   Version: {config.get('system', 'version')}")
        print(f"   Phase: {config.get('system', 'current_phase')}")
        print(f"   Paper Mode: {config.get('system', 'paper_mode')}")
        
        # Test station access
        print("\n2. Station Status:")
        for i in range(1, 7):
            enabled = config.is_station_enabled(i)
            status = "✅ ENABLED" if enabled else "❌ DISABLED"
            print(f"   Station {i}: {status}")
        
        # Test edge features
        print("\n3. Sample Edge Features:")
        edges = ['whale_tracking', 'sarcasm_detection', 'pump_detection']
        for edge in edges:
            enabled = config.is_edge_enabled(edge)
            status = "✅ ENABLED" if enabled else "❌ DISABLED"
            print(f"   {edge}: {status}")
        
        # Test performance targets
        print("\n4. Performance Targets (Phase 0):")
        targets = config.get_performance_targets(0)
        print(f"   Win Rate: {targets.get('win_rate_percent', 'N/A')}%")
        print(f"   Avg Profit: ${targets.get('avg_profit_per_trade', 'N/A')}")
        print(f"   Monthly: ${targets.get('monthly_profit_target', 'N/A')}")
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("=" * 60)
