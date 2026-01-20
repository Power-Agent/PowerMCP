"""
Unit tests for PyPSA MCP Server

Run with: pytest test_pypsa_mcp.py -v
"""

import pytest
import json
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np
from pypsa import Network

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pypsa_mcp import (
    get_network_info,
    get_component_details,
    create_network,
    add_bus,
    add_generator,
    add_load,
    add_line,
    add_storage_unit,
    import_from_csv_folder,
    export_to_csv_folder,
)


class TestPyPSAMCP:
    """Test suite for PyPSA MCP functions"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def sample_network_file(self, temp_dir):
        """Create a sample network file for testing"""
        network = Network()
        network.add("Bus", "Bus_1", v_nom=380)
        network.add("Bus", "Bus_2", v_nom=380)
        network.add("Generator", "Gen_1", bus="Bus_1", p_nom=100, marginal_cost=50)
        network.add("Load", "Load_1", bus="Bus_2", p_set=80)
        network.add("Line", "Line_1", bus0="Bus_1", bus1="Bus_2", x=0.1, s_nom=100)
        
        network_file = os.path.join(temp_dir, "test_network.nc")
        network.export_to_netcdf(network_file)
        return network_file
        
    def test_get_network_info(self, sample_network_file):
        """Test getting network information"""
        result = get_network_info(sample_network_file)
        info = json.loads(result)
        
        assert info["buses"] == 2
        assert info["generators"] == 1
        assert info["loads"] == 1
        assert info["lines"] == 1
        assert "components" in info
    
    def test_get_component_details_all(self, sample_network_file):
        """Test getting all components of a type"""
        result = get_component_details(sample_network_file, "buses")
        buses = json.loads(result)
        
        assert "Bus_1" in buses
        assert "Bus_2" in buses
        assert buses["Bus_1"]["v_nom"] == 380.0
    
    def test_get_component_details_specific(self, sample_network_file):
        """Test getting specific component details"""
        result = get_component_details(sample_network_file, "generators", "Gen_1")
        gen = json.loads(result)
        
        assert gen["bus"] == "Bus_1"
        assert gen["p_nom"] == 100.0
        assert gen["marginal_cost"] == 50.0
    
    def test_get_component_details_invalid(self, sample_network_file):
        """Test error handling for invalid component"""
        # Test invalid component type
        result = get_component_details(sample_network_file, "invalid_type")
        result_dict = json.loads(result)
        assert result_dict["status"] == "error"
        assert "invalid_type" in result_dict["message"]
        
        # Test invalid component ID
        result = get_component_details(sample_network_file, "buses", "Invalid_Bus")
        result_dict = json.loads(result)
        assert result_dict["status"] == "error"
        assert "Invalid_Bus" in result_dict["message"]
        
    def test_create_network(self, temp_dir):
        """Test creating a new network"""
        network_name = os.path.join(temp_dir, "new_network")
        snapshots = ["2024-01-01 00:00", "2024-01-01 01:00"]
        
        result = create_network(network_name, snapshots=snapshots)
        response = json.loads(result)
        
        assert response["status"] == "success"
        assert os.path.exists(f"{network_name}.nc")
        
        network = Network(f"{network_name}.nc")
        assert len(network.snapshots) == 2
    
    def test_add_bus(self, sample_network_file):
        """Test adding a bus to the network"""
        result = add_bus(sample_network_file, "Bus_3", v_nom=110, x=5, y=10)
        response = json.loads(result)
        
        assert response["status"] == "success"
        
        # Verify bus was added
        network = Network(sample_network_file)
        assert "Bus_3" in network.buses.index
        assert network.buses.loc["Bus_3", "v_nom"] == 110
    
    def test_add_generator(self, sample_network_file):
        """Test adding a generator"""
        result = add_generator(
            sample_network_file, 
            "Gen_2", 
            bus="Bus_2", 
            p_nom=200, 
            marginal_cost=30,
            carrier="wind"
        )
        response = json.loads(result)
        
        assert response["status"] == "success"
        
        network = Network(sample_network_file)
        assert "Gen_2" in network.generators.index
        assert network.generators.loc["Gen_2", "p_nom"] == 200
        assert network.generators.loc["Gen_2", "carrier"] == "wind"
    
    def test_add_load(self, sample_network_file):
        """Test adding a load"""
        result = add_load(sample_network_file, "Load_2", bus="Bus_1", p_set=50)
        response = json.loads(result)
        
        assert response["status"] == "success"
        
        network = Network(sample_network_file)
        assert "Load_2" in network.loads.index
        assert network.loads.loc["Load_2", "p_set"] == 50
    
    def test_add_line(self, sample_network_file):
        """Test adding a transmission line"""

        add_bus(sample_network_file, "Bus_3", v_nom=380)
        
        result = add_line(
            sample_network_file,
            "Line_2",
            bus0="Bus_2",
            bus1="Bus_3",
            x=0.2,
            r=0.02,
            s_nom=150
        )
        response = json.loads(result)
        
        assert response["status"] == "success"
        
        network = Network(sample_network_file)
        assert "Line_2" in network.lines.index
        assert network.lines.loc["Line_2", "x"] == 0.2
    
    def test_add_storage_unit(self, sample_network_file):
        """Test adding a storage unit"""
        result = add_storage_unit(
            sample_network_file,
            "Storage_1",
            bus="Bus_1",
            p_nom=50,
            max_hours=4,
            efficiency_store=0.95
        )
        response = json.loads(result)
        
        assert response["status"] == "success"
        
        network = Network(sample_network_file)
        assert "Storage_1" in network.storage_units.index
        assert network.storage_units.loc["Storage_1", "p_nom"] == 50
        assert network.storage_units.loc["Storage_1", "max_hours"] == 4

        
    def test_import_export_csv(self, temp_dir, sample_network_file):
        """Test CSV import and export"""
        csv_folder = os.path.join(temp_dir, "csv_export")
        
        # Test export
        result = export_to_csv_folder(sample_network_file, csv_folder)
        response = json.loads(result)
        assert response["status"] == "success"
        assert os.path.exists(csv_folder)
        assert os.path.exists(os.path.join(csv_folder, "buses.csv"))
        
        # Test import
        with patch('pypsa.Network.import_from_csv_folder'):
            with patch('pypsa.Network.export_to_netcdf'):
                result = import_from_csv_folder(csv_folder)
                response = json.loads(result)
                assert response["status"] == "success"


class TestPyPSAMCPIntegration:
    """Integration tests for complete workflows"""
    
    @pytest.fixture
    def integration_dir(self):
        """Create a directory for integration tests"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    # Using pytest
    pytest.main([__file__, "-v"])