"""
Fusion Configuration Management

Provides flexible configuration for the multimodal fusion pipeline
with environment variables, JSON config files, and sensible defaults.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional


class FusionConfig:
    """
    Manages fusion configuration with multiple sources:
    1. Default configuration
    2. JSON config file
    3. Environment variables (highest priority)
    """
    
    # Default configuration
    DEFAULT_CONFIG = {
        # Core fusion settings
        'enable_fusion': False,
        'embedding_dim': 4096,
        'num_attention_heads': 8,
        
        # Fusion behavior
        'fusion_mode': 'adaptive',  # 'adaptive', 'always', 'threshold'
        'confidence_threshold': 0.7,
        'use_simplified_attention': False,
        'cache_projections': True,
        
        # Quality thresholds
        'min_fusion_quality': 0.3,
        'prefer_docai_threshold': 0.85,
        'prefer_vision_threshold': 0.6,
        
        # Performance settings
        'max_cache_size_mb': 100,
        'projection_timeout_s': 5.0,
        'fusion_timeout_s': 10.0,
        
        # Debug and monitoring
        'enable_diagnostics': False,
        'log_fusion_metrics': True,
        'metrics_report_interval': 100,  # Report every N fusions
        
        # Feature extraction
        'extract_layout_features': True,
        'extract_table_features': True, 
        'extract_field_features': True,
        'extract_relationship_features': True,
        'extract_confidence_features': True,
        
        # Advanced settings
        'cross_attention_dropout': 0.0,
        'projection_seed': 42,  # For reproducible hash projections
        'normalize_embeddings': True,
        'use_residual_connections': False
    }
    
    # Environment variable mappings
    ENV_MAPPINGS = {
        'ENABLE_FUSION': ('enable_fusion', bool),
        'FUSION_EMBEDDING_DIM': ('embedding_dim', int),
        'FUSION_NUM_HEADS': ('num_attention_heads', int),
        'FUSION_MODE': ('fusion_mode', str),
        'FUSION_CONFIDENCE_THRESHOLD': ('confidence_threshold', float),
        'FUSION_USE_SIMPLIFIED': ('use_simplified_attention', bool),
        'FUSION_CACHE_PROJECTIONS': ('cache_projections', bool),
        'FUSION_MIN_QUALITY': ('min_fusion_quality', float),
        'FUSION_ENABLE_DIAGNOSTICS': ('enable_diagnostics', bool),
        'FUSION_LOG_METRICS': ('log_fusion_metrics', bool)
    }
    
    def __init__(
        self, 
        config_file: Optional[Path] = None,
        override_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize fusion configuration.
        
        Args:
            config_file: Optional path to JSON config file
            override_config: Optional dictionary to override settings
        """
        # Start with defaults
        self.config = self.DEFAULT_CONFIG.copy()
        
        # Load from JSON file if provided
        if config_file and config_file.exists():
            self._load_json_config(config_file)
        
        # Apply overrides if provided
        if override_config:
            self.config.update(override_config)
        
        # Apply environment variables (highest priority)
        self._load_env_config()
        
        # Validate configuration
        self._validate_config()
    
    def _load_json_config(self, config_file: Path):
        """Load configuration from JSON file."""
        try:
            with open(config_file, 'r') as f:
                json_config = json.load(f)
            
            # Only update with valid keys
            for key, value in json_config.items():
                if key in self.DEFAULT_CONFIG:
                    self.config[key] = value
                else:
                    print(f"  ⚠️ Unknown config key ignored: {key}")
        except Exception as e:
            print(f"  ⚠️ Failed to load config file {config_file}: {e}")
    
    def _load_env_config(self):
        """Load configuration from environment variables."""
        for env_var, (config_key, converter) in self.ENV_MAPPINGS.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    if converter == bool:
                        # Special handling for boolean values
                        self.config[config_key] = value.lower() in ['true', '1', 'yes', 'on']
                    else:
                        self.config[config_key] = converter(value)
                except ValueError as e:
                    print(f"  ⚠️ Invalid value for {env_var}: {value} ({e})")
    
    def _validate_config(self):
        """Validate configuration values."""
        # Embedding dimension must be divisible by num_heads
        if self.config['embedding_dim'] % self.config['num_attention_heads'] != 0:
            raise ValueError(
                f"embedding_dim ({self.config['embedding_dim']}) must be divisible by "
                f"num_attention_heads ({self.config['num_attention_heads']})"
            )
        
        # Validate thresholds
        for threshold_key in ['confidence_threshold', 'min_fusion_quality', 
                             'prefer_docai_threshold', 'prefer_vision_threshold']:
            value = self.config[threshold_key]
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{threshold_key} must be between 0 and 1, got {value}")
        
        # Validate fusion mode
        valid_modes = ['adaptive', 'always', 'threshold']
        if self.config['fusion_mode'] not in valid_modes:
            raise ValueError(
                f"fusion_mode must be one of {valid_modes}, got {self.config['fusion_mode']}"
            )
        
        # Validate timeouts
        for timeout_key in ['projection_timeout_s', 'fusion_timeout_s']:
            if self.config[timeout_key] <= 0:
                raise ValueError(f"{timeout_key} must be positive, got {self.config[timeout_key]}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)
    
    def update(self, updates: Dict[str, Any]):
        """Update configuration with new values."""
        self.config.update(updates)
        self._validate_config()
    
    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary."""
        return self.config.copy()
    
    def save_to_json(self, output_path: Path):
        """Save current configuration to JSON file."""
        with open(output_path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def print_config(self):
        """Print current configuration for debugging."""
        print("\n🔧 Fusion Configuration:")
        print("-" * 40)
        
        # Group by category
        categories = {
            'Core': ['enable_fusion', 'embedding_dim', 'num_attention_heads'],
            'Behavior': ['fusion_mode', 'confidence_threshold', 'use_simplified_attention'],
            'Quality': ['min_fusion_quality', 'prefer_docai_threshold', 'prefer_vision_threshold'],
            'Performance': ['cache_projections', 'max_cache_size_mb', 'projection_timeout_s'],
            'Debug': ['enable_diagnostics', 'log_fusion_metrics', 'metrics_report_interval']
        }
        
        for category, keys in categories.items():
            print(f"\n{category}:")
            for key in keys:
                if key in self.config:
                    print(f"  • {key}: {self.config[key]}")
        
        print("-" * 40)
    
    @classmethod
    def load_default(cls) -> 'FusionConfig':
        """Load default configuration with environment overrides."""
        return cls()
    
    @classmethod
    def load_from_file(cls, config_file: Path) -> 'FusionConfig':
        """Load configuration from JSON file."""
        return cls(config_file=config_file)
    
    @classmethod
    def create_sample_config(cls, output_path: Path):
        """Create a sample configuration file."""
        sample_config = {
            "enable_fusion": True,
            "embedding_dim": 4096,
            "num_attention_heads": 8,
            "fusion_mode": "adaptive",
            "confidence_threshold": 0.7,
            "use_simplified_attention": False,
            "cache_projections": True,
            "enable_diagnostics": False,
            "log_fusion_metrics": True,
            "_comment": "This is a sample fusion configuration file. Modify as needed."
        }
        
        with open(output_path, 'w') as f:
            json.dump(sample_config, f, indent=2)
        
        print(f"✅ Sample config created at: {output_path}")


# Singleton instance for global configuration
_global_config: Optional[FusionConfig] = None


def get_fusion_config() -> FusionConfig:
    """Get global fusion configuration instance."""
    global _global_config
    if _global_config is None:
        # Check for config file in standard locations
        config_locations = [
            Path.cwd() / 'fusion_config.json',
            Path.home() / '.config' / 'fusion' / 'config.json',
            Path('/etc/fusion/config.json')
        ]
        
        config_file = None
        for location in config_locations:
            if location.exists():
                config_file = location
                break
        
        _global_config = FusionConfig(config_file=config_file)
    
    return _global_config


def set_fusion_config(config: FusionConfig):
    """Set global fusion configuration instance."""
    global _global_config
    _global_config = config


def reset_fusion_config():
    """Reset global configuration to defaults."""
    global _global_config
    _global_config = None