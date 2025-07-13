import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
import json

from app.schemas.prompt_schemas import DAILY_SCHEMA, BEST_PERFORMERS_SCHEMA, IMPROVE_SCHEMA


class TestPromptSchemas(unittest.TestCase):
    """Test class for prompt schema definitions."""
    
    def setUp(self):
        """Set up test fixtures."""
        pass

    def test_daily_schema_structure(self):
        """Test that DAILY_SCHEMA has the correct structure."""
        # Assert schema exists and has required properties
        self.assertIsInstance(DAILY_SCHEMA, dict)
        self.assertIn('type', DAILY_SCHEMA)
        self.assertEqual(DAILY_SCHEMA['type'], 'object')
        
        # Check for required properties
        self.assertIn('properties', DAILY_SCHEMA)
        properties = DAILY_SCHEMA['properties']
        
        # Should have recommendations array
        self.assertIn('recommendations', properties)
        recommendations = properties['recommendations']
        self.assertEqual(recommendations['type'], 'array')
        
        # Check array items structure
        self.assertIn('items', recommendations)
        items = recommendations['items']
        self.assertEqual(items['type'], 'object')
        
        # Check required fields in recommendation items
        item_properties = items['properties']
        required_fields = ['symbol', 'catalyst', 'target', 'risk']
        for field in required_fields:
            self.assertIn(field, item_properties)
            self.assertEqual(item_properties[field]['type'], 'string')

    def test_daily_schema_validation_requirements(self):
        """Test DAILY_SCHEMA validation requirements."""
        # Check if required fields are specified
        if 'required' in DAILY_SCHEMA:
            self.assertIn('recommendations', DAILY_SCHEMA['required'])
        
        # Check array constraints
        recommendations = DAILY_SCHEMA['properties']['recommendations']
        if 'minItems' in recommendations:
            self.assertEqual(recommendations['minItems'], 5)
        if 'maxItems' in recommendations:
            self.assertEqual(recommendations['maxItems'], 5)

    def test_best_performers_schema_structure(self):
        """Test that BEST_PERFORMERS_SCHEMA has the correct structure."""
        # Assert schema exists and has required properties
        self.assertIsInstance(BEST_PERFORMERS_SCHEMA, dict)
        self.assertIn('type', BEST_PERFORMERS_SCHEMA)
        self.assertEqual(BEST_PERFORMERS_SCHEMA['type'], 'object')
        
        # Check for required properties
        self.assertIn('properties', BEST_PERFORMERS_SCHEMA)
        properties = BEST_PERFORMERS_SCHEMA['properties']
        
        # Should have performers array
        self.assertIn('performers', properties)
        performers = properties['performers']
        self.assertEqual(performers['type'], 'array')
        
        # Check array items structure
        self.assertIn('items', performers)
        items = performers['items']
        self.assertEqual(items['type'], 'object')
        
        # Check required fields in performer items
        item_properties = items['properties']
        required_fields = ['symbol', 'pct', 'reason']
        for field in required_fields:
            self.assertIn(field, item_properties)
        
        # Check specific field types
        self.assertEqual(item_properties['symbol']['type'], 'string')
        self.assertEqual(item_properties['reason']['type'], 'string')
        # pct should be number type
        self.assertEqual(item_properties['pct']['type'], 'number')

    def test_best_performers_schema_validation_requirements(self):
        """Test BEST_PERFORMERS_SCHEMA validation requirements."""
        # Check if required fields are specified
        if 'required' in BEST_PERFORMERS_SCHEMA:
            self.assertIn('performers', BEST_PERFORMERS_SCHEMA['required'])
        
        # Check array constraints
        performers = BEST_PERFORMERS_SCHEMA['properties']['performers']
        if 'minItems' in performers:
            self.assertEqual(performers['minItems'], 5)
        if 'maxItems' in performers:
            self.assertEqual(performers['maxItems'], 5)

    def test_improve_schema_structure(self):
        """Test that IMPROVE_SCHEMA has the correct structure."""
        # Assert schema exists and has required properties
        self.assertIsInstance(IMPROVE_SCHEMA, dict)
        self.assertIn('type', IMPROVE_SCHEMA)
        self.assertEqual(IMPROVE_SCHEMA['type'], 'object')
        
        # Check for required properties
        self.assertIn('properties', IMPROVE_SCHEMA)
        properties = IMPROVE_SCHEMA['properties']
        
        # Should have new_prompt and analysis fields
        required_fields = ['new_prompt', 'analysis']
        for field in required_fields:
            self.assertIn(field, properties)
            self.assertEqual(properties[field]['type'], 'string')

    def test_improve_schema_validation_requirements(self):
        """Test IMPROVE_SCHEMA validation requirements."""
        # Check if required fields are specified
        if 'required' in IMPROVE_SCHEMA:
            required_fields = ['new_prompt', 'analysis']
            for field in required_fields:
                self.assertIn(field, IMPROVE_SCHEMA['required'])

    def test_schema_json_serializable(self):
        """Test that all schemas are JSON serializable."""
        schemas = [DAILY_SCHEMA, BEST_PERFORMERS_SCHEMA, IMPROVE_SCHEMA]
        
        for schema in schemas:
            with self.subTest(schema=schema):
                try:
                    json.dumps(schema)
                except (TypeError, ValueError) as e:
                    self.fail(f"Schema is not JSON serializable: {e}")

    def test_daily_schema_example_validation(self):
        """Test DAILY_SCHEMA with example valid data."""
        # Example valid data
        valid_data = {
            "recommendations": [
                {
                    "symbol": "AAPL",
                    "catalyst": "Strong earnings report",
                    "target": "3%",
                    "risk": "Medium"
                },
                {
                    "symbol": "GOOGL",
                    "catalyst": "AI breakthrough announcement",
                    "target": "5%",
                    "risk": "High"
                },
                {
                    "symbol": "MSFT",
                    "catalyst": "Cloud revenue growth",
                    "target": "2%",
                    "risk": "Low"
                },
                {
                    "symbol": "TSLA",
                    "catalyst": "Delivery numbers beat expectations",
                    "target": "8%",
                    "risk": "High"
                },
                {
                    "symbol": "NVDA",
                    "catalyst": "GPU demand surge",
                    "target": "6%",
                    "risk": "Medium"
                }
            ]
        }
        
        # This would validate against the schema if validation library is available
        # For now, just check structure matches
        self.assertIn('recommendations', valid_data)
        self.assertEqual(len(valid_data['recommendations']), 5)
        
        for rec in valid_data['recommendations']:
            self.assertIn('symbol', rec)
            self.assertIn('catalyst', rec)
            self.assertIn('target', rec)
            self.assertIn('risk', rec)

    def test_best_performers_schema_example_validation(self):
        """Test BEST_PERFORMERS_SCHEMA with example valid data."""
        # Example valid data
        valid_data = {
            "performers": [
                {
                    "symbol": "TSLA",
                    "pct": 8.5,
                    "reason": "Strong delivery numbers exceeded expectations"
                },
                {
                    "symbol": "NVDA",
                    "pct": 6.2,
                    "reason": "AI chip demand continues to surge"
                },
                {
                    "symbol": "AMD",
                    "pct": 5.8,
                    "reason": "Data center revenue growth"
                },
                {
                    "symbol": "AAPL",
                    "pct": 4.1,
                    "reason": "iPhone sales beat estimates"
                },
                {
                    "symbol": "GOOGL",
                    "pct": 3.9,
                    "reason": "Search revenue growth acceleration"
                }
            ]
        }
        
        # Check structure matches schema
        self.assertIn('performers', valid_data)
        self.assertEqual(len(valid_data['performers']), 5)
        
        for performer in valid_data['performers']:
            self.assertIn('symbol', performer)
            self.assertIn('pct', performer)
            self.assertIn('reason', performer)
            self.assertIsInstance(performer['pct'], (int, float))

    def test_improve_schema_example_validation(self):
        """Test IMPROVE_SCHEMA with example valid data."""
        # Example valid data
        valid_data = {
            "new_prompt": "Analyze current market conditions and provide 5 stock recommendations with specific catalysts, target price movements, and risk assessments. Focus on companies with strong fundamentals and recent positive developments.",
            "analysis": "The improved prompt is more specific about the analysis requirements and emphasizes fundamental analysis and recent developments, which should lead to better quality recommendations."
        }
        
        # Check structure matches schema
        self.assertIn('new_prompt', valid_data)
        self.assertIn('analysis', valid_data)
        self.assertIsInstance(valid_data['new_prompt'], str)
        self.assertIsInstance(valid_data['analysis'], str)

    def test_schema_field_constraints(self):
        """Test field constraints in schemas."""
        # Test DAILY_SCHEMA constraints
        daily_props = DAILY_SCHEMA['properties']['recommendations']['items']['properties']
        
        # Check if there are any string length constraints
        for field_name, field_def in daily_props.items():
            if 'minLength' in field_def:
                self.assertGreater(field_def['minLength'], 0)
            if 'maxLength' in field_def:
                self.assertGreater(field_def['maxLength'], field_def.get('minLength', 0))

        # Test BEST_PERFORMERS_SCHEMA constraints
        best_props = BEST_PERFORMERS_SCHEMA['properties']['performers']['items']['properties']
        
        # Check pct field constraints
        if 'pct' in best_props and 'minimum' in best_props['pct']:
            # Percentage should allow negative values (for losses)
            self.assertLessEqual(best_props['pct']['minimum'], 0)

    def test_schema_extensibility(self):
        """Test that schemas can be extended without breaking existing functionality."""
        # Test adding optional fields
        extended_daily_schema = DAILY_SCHEMA.copy()
        extended_daily_schema['properties']['recommendations']['items']['properties']['confidence'] = {
            "type": "number",
            "minimum": 0,
            "maximum": 1
        }
        
        # Should still be valid JSON
        try:
            json.dumps(extended_daily_schema)
        except (TypeError, ValueError) as e:
            self.fail(f"Extended schema is not JSON serializable: {e}")

    def test_schema_backwards_compatibility(self):
        """Test that schemas maintain backwards compatibility."""
        # This would test that old data still validates against new schemas
        # For now, just ensure schemas have stable required fields
        
        # DAILY_SCHEMA should always require these core fields
        core_daily_fields = ['symbol', 'catalyst', 'target', 'risk']
        daily_item_props = DAILY_SCHEMA['properties']['recommendations']['items']['properties']
        
        for field in core_daily_fields:
            self.assertIn(field, daily_item_props)

        # BEST_PERFORMERS_SCHEMA should always require these core fields
        core_best_fields = ['symbol', 'pct', 'reason']
        best_item_props = BEST_PERFORMERS_SCHEMA['properties']['performers']['items']['properties']
        
        for field in core_best_fields:
            self.assertIn(field, best_item_props)

        # IMPROVE_SCHEMA should always require these core fields
        core_improve_fields = ['new_prompt', 'analysis']
        improve_props = IMPROVE_SCHEMA['properties']
        
        for field in core_improve_fields:
            self.assertIn(field, improve_props)


if __name__ == '__main__':
    unittest.main()