#!/usr/bin/env python3
"""
OSM Data Loader for DC Metro Escalators

Fetches escalators from the DC Metro system using the Overpass API.
Focuses on outdoor escalators (highway=steps with conveying=* tags).
"""

import requests
import xml.etree.ElementTree as ET
import csv
import sys
from typing import List, Dict, Optional
from datetime import datetime
import argparse


class OSMEscalatorLoader:
    def __init__(self):
        self.overpass_url = "https://overpass-api.de/api/interpreter"
        
    def build_overpass_query(self, bbox: Optional[str] = None) -> str:
        """
        Build Overpass QL query for DC Metro escalators.
        
        Args:
            bbox: Optional bounding box in format "south,west,north,east"
                 If None, uses DC Metro area bounds
        """
        # DC Metro area bounding box (roughly covers DC, Northern VA, Southern MD)
        if bbox is None:
            bbox = "38.7,-77.3,39.0,-76.9"  # south,west,north,east
            
        query = f"""
        [out:xml][timeout:30];
        (
          way["highway"="steps"]["conveying"]["indoor"!="yes"]({bbox});
          way["highway"="steps"]["conveying"]["level"]({bbox});
          way["conveying"="reversible"]["highway"="steps"]({bbox});
          way["conveying"="up"]["highway"="steps"]({bbox});
          way["conveying"="down"]["highway"="steps"]({bbox});
        );
        out geom meta;
        """
        return query
        
    def fetch_osm_data(self, query: str) -> str:
        """Fetch data from Overpass API."""
        print(f"Fetching escalator data from Overpass API...")
        
        response = requests.post(
            self.overpass_url,
            data={'data': query},
            timeout=60
        )
        response.raise_for_status()
        
        print(f"Retrieved {len(response.content)} bytes of OSM data")
        return response.text
        
    def parse_osm_xml(self, xml_content: str) -> List[Dict]:
        """Parse OSM XML and extract escalator data."""
        print("Parsing OSM XML data...")
        
        root = ET.fromstring(xml_content)
        escalators = []
        
        for way in root.findall('way'):
            way_data = {
                'id': way.get('id'),
                'version': way.get('version'),
                'changeset': way.get('changeset'),
                'timestamp': way.get('timestamp'),
                'user': way.get('user'),
                'uid': way.get('uid'),
                'visible': way.get('visible', 'true'),
                'nodes': [],
                'tags': {},
                'lat': None,
                'lon': None,
                'name': '',
                'conveying': '',
                'highway': '',
                'incline': '',
                'indoor': '',
                'level': '',
                'all_tags': ''
            }
            
            # Extract node references
            for nd in way.findall('nd'):
                way_data['nodes'].append(nd.get('ref'))
                
            # Extract tags
            for tag in way.findall('tag'):
                key = tag.get('k')
                value = tag.get('v')
                way_data['tags'][key] = value
                
                # Map common tags to direct fields
                if key == 'name':
                    way_data['name'] = value
                elif key == 'conveying':
                    way_data['conveying'] = value
                elif key == 'highway':
                    way_data['highway'] = value
                elif key == 'incline':
                    way_data['incline'] = value
                elif key == 'indoor':
                    way_data['indoor'] = value
                elif key == 'level':
                    way_data['level'] = value
                    
            # Create a semicolon-separated string of all tags
            way_data['all_tags'] = ';'.join([f"{k}={v}" for k, v in way_data['tags'].items()])
            
            # Calculate approximate center coordinates from first node with coordinates
            first_nd = way.find('nd')
            if first_nd is not None:
                way_data['lat'] = first_nd.get('lat')
                way_data['lon'] = first_nd.get('lon')
                
            escalators.append(way_data)
            
        print(f"Found {len(escalators)} escalator ways")
        return escalators
        
    def save_to_csv(self, escalators: List[Dict], filename: str) -> None:
        """Save escalator data to CSV file."""
        print(f"Saving data to {filename}...")
        
        fieldnames = [
            'id', 'name', 'type', 'lat', 'lon', 'tags',
            'version', 'changeset', 'timestamp', 'user', 'uid', 'visible',
            'conveying', 'highway', 'incline', 'indoor', 'level', 'node_count'
        ]
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for escalator in escalators:
                row = {
                    'id': escalator['id'],
                    'name': escalator['name'] or f"Escalator {escalator['id']}",
                    'type': 'way',  # All our results are ways
                    'lat': escalator['lat'],
                    'lon': escalator['lon'],
                    'tags': escalator['all_tags'],
                    'version': escalator['version'],
                    'changeset': escalator['changeset'],
                    'timestamp': escalator['timestamp'],
                    'user': escalator['user'],
                    'uid': escalator['uid'],
                    'visible': escalator['visible'],
                    'conveying': escalator['conveying'],
                    'highway': escalator['highway'],
                    'incline': escalator['incline'],
                    'indoor': escalator['indoor'],
                    'level': escalator['level'],
                    'node_count': len(escalator['nodes'])
                }
                writer.writerow(row)
                
        print(f"Successfully saved {len(escalators)} escalators to {filename}")
        
    def load_escalators(self, bbox: Optional[str] = None, output_file: str = "src/data/dc_metro_escalators.csv") -> List[Dict]:
        """Main method to load escalator data."""
        try:
            # Build and execute query
            query = self.build_overpass_query(bbox)
            xml_data = self.fetch_osm_data(query)
            
            # Parse and process data
            escalators = self.parse_osm_xml(xml_data)
            
            if escalators:
                self.save_to_csv(escalators, output_file)
                print(f"\n✅ Successfully loaded {len(escalators)} DC Metro escalators!")
                print(f"📁 Data saved to: {output_file}")
            else:
                print("⚠️  No escalators found with the current query")
                
            return escalators
            
        except requests.RequestException as e:
            print(f"❌ Error fetching data from Overpass API: {e}")
            sys.exit(1)
        except ET.ParseError as e:
            print(f"❌ Error parsing OSM XML: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Load DC Metro escalator data from OSM')
    parser.add_argument('--bbox', type=str, help='Bounding box in format "south,west,north,east"')
    parser.add_argument('--output', type=str, default='src/data/dc_metro_escalators.csv', 
                       help='Output CSV file path')
    parser.add_argument('--preview', action='store_true', help='Show first 5 results without saving')
    
    args = parser.parse_args()
    
    loader = OSMEscalatorLoader()
    escalators = loader.load_escalators(bbox=args.bbox, output_file=args.output)
    
    if args.preview and escalators:
        print(f"\n📋 Preview of first 5 escalators:")
        print("-" * 80)
        for i, escalator in enumerate(escalators[:5]):
            print(f"{i+1}. ID: {escalator['id']}")
            print(f"   Name: {escalator['name']}")
            print(f"   Conveying: {escalator['conveying']}")
            print(f"   Location: {escalator['lat']}, {escalator['lon']}")
            print(f"   Tags: {escalator['all_tags'][:100]}{'...' if len(escalator['all_tags']) > 100 else ''}")
            print()


if __name__ == "__main__":
    main()