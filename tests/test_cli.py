"""Tests for CLI commands"""

import pytest
from typer.testing import CliRunner
from pathlib import Path
import sys
from unittest.mock import patch, MagicMock, PropertyMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from openrag.cli import app
from openrag import __version__


class TestCLI:
    """Test command line interface"""
    
    @pytest.fixture
    def runner(self):
        return CliRunner()
    
    def test_help(self, runner):
        """Test --help flag"""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "OpenRAG" in result.stdout
        assert "Commands" in result.stdout
    
    def test_version_command(self, runner):
        """Test version command"""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert f"OpenRAG version: {__version__}" in result.stdout
    
    @patch('psutil.process_iter')
    @patch('psutil.net_connections')
    def test_status_command_no_services(self, mock_net_connections, mock_process_iter, runner):
        """Test status command when no services are running"""
        # Mock no ChromaDB processes
        mock_process_iter.return_value = []
        
        # Mock no query server connections
        mock_net_connections.return_value = []
        
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "ChromaDB: Not running" in result.stdout
        assert "Query Server: Not running" in result.stdout
    
    @patch('openrag.cli.ProcessManager.kill_existing')
    def test_down_command_no_services(self, mock_kill, runner):
        """Test down command when no services are running"""
        mock_kill.return_value = False
        
        result = runner.invoke(app, ["down"])
        assert result.exit_code == 0
        assert "No running services found" in result.stdout
        assert "OpenRAG stopped" in result.stdout
    
    @patch('openrag.cli.ProcessManager.kill_existing')
    def test_down_command_with_services(self, mock_kill, runner):
        """Test down command when services are running"""
        mock_kill.side_effect = [True, True]  # First for ChromaDB, second for query server
        
        result = runner.invoke(app, ["down"])
        assert result.exit_code == 0
        assert "Stopped ChromaDB" in result.stdout
        assert "Stopped query server" in result.stdout
        assert "OpenRAG stopped" in result.stdout
    
    @patch('openrag.cli.ChromaCollectionManager')
    @patch('openrag.cli.FileWatcher')
    @patch('openrag.cli.typer.echo')  # Mock typer.echo to avoid output
    def test_init_command(self, mock_echo, mock_file_watcher, mock_collection_manager, runner, temp_project):
        """Test init command"""
        mock_manager = MagicMock()
        mock_manager.get_collection_info.return_value = {"count": 42}
        mock_collection_manager.return_value = mock_manager
        
        mock_watcher = MagicMock()
        mock_watcher.initial_index.return_value = 5
        mock_file_watcher.return_value = mock_watcher
        
        result = runner.invoke(app, [
            "init",
            "--project", str(temp_project),
            "--collection", "test_cli"
        ])
        
        assert result.exit_code == 0
    

@patch('openrag.cli.typer.Exit')
@patch('openrag.cli.typer.echo')
@patch('openrag.cli.OpenRAGConfig')
@patch('openrag.cli.QueryServer')
@patch('openrag.cli.FileWatcher')
@patch('openrag.cli.ChromaCollectionManager')
@patch('openrag.cli.ChromaServer')
@patch('openrag.cli.setup_logging')
def test_up_command_save_config(self, mock_logging, mock_chroma, mock_manager, 
                                mock_watcher, mock_query, mock_config, 
                                mock_echo, mock_exit, runner, tmp_path):
    """Test up command with save-config"""
    config_path = tmp_path / "test-config.json"
    
    # Mock config instance
    mock_config_instance = MagicMock()
    mock_config.return_value = mock_config_instance
    
    # Mock logging
    mock_logging.return_value = {
        "chroma": MagicMock(),
        "indexer": MagicMock(),
        "query": MagicMock()
    }
    
    # Mock ChromaServer to succeed
    mock_chroma_instance = MagicMock()
    mock_chroma_instance.start.return_value = True
    mock_chroma.return_value = mock_chroma_instance
    
    # Mock CollectionManager
    mock_manager_instance = MagicMock()
    mock_manager.return_value = mock_manager_instance
    
    # Mock that save_config is called and then raises Exit
    mock_exit.side_effect = SystemExit(0)
    
    result = runner.invoke(app, [
        "up",
        "--project", str(tmp_path),
        "--collection", "test_cli",
        "--chunk-size", "1500",
        "--save-config", str(config_path),
    ])
    
    # Should try to save the config
    assert mock_config_instance.save.called
    assert result.exit_code == 0



    def test_up_command_help(self, runner):
        """Test up command help"""
        result = runner.invoke(app, ["up", "--help"])
        assert result.exit_code == 0
        assert "Start OpenRAG services" in result.stdout
    
    @patch('openrag.cli.setup_logging')
    @patch('openrag.cli.ChromaServer')
    @patch('openrag.cli.ChromaCollectionManager')
    @patch('openrag.cli.FileWatcher')
    @patch('openrag.cli.QueryServer')
    @patch('openrag.cli.typer.echo')
    def test_up_command_basic(self, mock_echo, mock_query, mock_watcher, mock_manager, mock_chroma, mock_logging, runner, temp_project):
        """Test up command with basic args"""
        mock_logging.return_value = {
            "chroma": MagicMock(),
            "indexer": MagicMock(),
            "query": MagicMock()
        }
        
        mock_chroma_instance = MagicMock()
        mock_chroma_instance.start.return_value = True
        mock_chroma.return_value = mock_chroma_instance
        
        mock_manager_instance = MagicMock()
        mock_manager.return_value = mock_manager_instance
        
        mock_query_instance = MagicMock()
        mock_query_instance.start.side_effect = KeyboardInterrupt()
        mock_query.return_value = mock_query_instance
        
        result = runner.invoke(app, [
            "up",
            "--project", str(temp_project),
            "--no-initial-index",
            "--quiet"
        ])
        
        assert result.exit_code == 0
