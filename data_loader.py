#!/usr/bin/env python3
"""
OSM Data Loader for DC Metro Escalators

Fetches escalators from the DC Metro system using the Overpass API.
Focuses on outdoor escalators (highway=steps with conveying=* tags).
"""

import requests
import xml.etree.ElementTree as ET
import sys
import numpy as np
import pandas as pd
import pvlib
from typing import List, Dict, Optional
import argparse
import math


class OSMEscalatorLoader:
    def __init__(self):
        self.overpass_url = "https://overpass-api.de/api/interpreter"
        
    def build_overpass_query(self, bbox: Optional[str] = None) -> str:
        """
        Build Overpass QL query for DC Metro escalators and nearby stations.
        
        Args:
            bbox: Optional bounding box in format "south,west,north,east"
                 If None, uses DC Metro area bounds
        """
        # DC Metro area bounding box (roughly covers DC, Northern VA, Southern MD)
        if bbox is None:
            bbox = "38.7,-77.3,39.0,-76.9"  # south,west,north,east
            
        query = f"""
        [out:xml][timeout:60];
        (
          way["highway"="steps"]["conveying"]["indoor"!="yes"]({bbox});
          way["highway"="steps"]["conveying"]["level"]({bbox});
          way["conveying"="reversible"]["highway"="steps"]({bbox});
          way["conveying"="up"]["highway"="steps"]({bbox});
          way["conveying"="down"]["highway"="steps"]({bbox});
          
          node["railway"="station"]["station"="subway"]({bbox});
          node["public_transport"="station"]["subway"="yes"]({bbox});
          node["railway"="subway_entrance"]({bbox});
          node["name"]["railway"]({bbox});
          node["name"]["public_transport"="station"]({bbox});
        );
        (._;>;);
        
        out meta;
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
        """Parse OSM XML and extract escalator data with node coordinates and station names."""
        print("Parsing OSM XML data...")
        
        root = ET.fromstring(xml_content)
        
        # First, build a dictionary of all nodes with their coordinates and tags
        nodes = {}
        station_nodes = {}
        
        for node in root.findall('node'):
            node_id = node.get('id')
            node_data = {
                'lat': float(node.get('lat')),
                'lon': float(node.get('lon')),
                'tags': {}
            }
            
            # Extract tags
            for tag in node.findall('tag'):
                key = tag.get('k')
                value = tag.get('v')
                node_data['tags'][key] = value
            
            nodes[node_id] = node_data
            
            # Track nodes that might be stations (have name tags)
            if 'name' in node_data['tags']:
                station_nodes[node_id] = node_data
        
        print(f"Found {len(nodes)} nodes ({len(station_nodes)} with names)")
        
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
                'node_refs': [],
                'node_coords': [],
                'tags': {},
                'lat': None,
                'lon': None,
                'name': '',
                'conveying': '',
                'highway': '',
                'incline': '',
                'indoor': '',
                'level': '',
                'all_tags': '',
                'azimuth': None,
                'top_lat': None,
                'top_lon': None,
                'solar_alignments': [],
                'station_name': ''
            }
            
            # Extract node references and their coordinates
            for nd in way.findall('nd'):
                node_ref = nd.get('ref')
                way_data['node_refs'].append(node_ref)
                if node_ref in nodes:
                    way_data['node_coords'].append(nodes[node_ref])
                
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
            
            # Calculate escalator orientation and coordinates
            if len(way_data['node_coords']) >= 2:
                start_coord = way_data['node_coords'][0]
                end_coord = way_data['node_coords'][-1]
                
                # Determine which end is the "outside" end of the escalator
                # We need to determine the orientation of the escalator correctly
                outside_coord, inside_coord = self.determine_escalator_direction(
                    start_coord, end_coord, way_data['tags']
                )
                
                way_data['top_lat'] = outside_coord['lat']
                way_data['top_lon'] = outside_coord['lon']
                way_data['azimuth'] = self.calculate_azimuth(inside_coord, outside_coord)
                
                # Use the center coordinate for general lat/lon
                way_data['lat'] = (start_coord['lat'] + end_coord['lat']) / 2
                way_data['lon'] = (start_coord['lon'] + end_coord['lon']) / 2
                
                # Calculate solar alignments
                way_data['solar_alignments'] = self.calculate_solar_alignments(
                    way_data['top_lat'], 
                    way_data['top_lon'], 
                    way_data['azimuth']
                )
                
                # Find the nearest station name from escalator endpoints
                way_data['station_name'] = self.find_station_name(way_data['node_refs'], nodes, station_nodes)
            else:
                # Fallback to first available coordinate
                if way_data['node_coords']:
                    first_coord = way_data['node_coords'][0]
                    way_data['lat'] = first_coord['lat']
                    way_data['lon'] = first_coord['lon']
                    way_data['top_lat'] = first_coord['lat']
                    way_data['top_lon'] = first_coord['lon']
                
                # Find station name even for single-node escalators
                way_data['station_name'] = self.find_station_name(way_data['node_refs'], nodes, station_nodes)
            
            # Filter out above-ground elevated stations (like Tysons)
            if self.is_underground_escalator(way_data['tags']):
                escalators.append(way_data)
            
        print(f"Found {len(escalators)} escalator ways")
        return escalators
    
    def calculate_azimuth(self, start_coord: Dict, end_coord: Dict) -> float:
        """Calculate azimuth (bearing) from start to end coordinate in degrees from North."""
        lat1 = math.radians(start_coord['lat'])
        lat2 = math.radians(end_coord['lat'])
        lon1 = math.radians(start_coord['lon'])
        lon2 = math.radians(end_coord['lon'])
        
        dlon = lon2 - lon1
        
        y = math.sin(dlon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        
        azimuth = math.atan2(y, x)
        azimuth = math.degrees(azimuth)
        azimuth = (azimuth + 360) % 360  # Normalize to 0-360
        
        return azimuth
    
    def is_underground_escalator(self, tags: Dict) -> bool:
        """
        Determine if this escalator serves an underground station.
        Above-ground elevated stations like Tysons should be filtered out.
        """
        # Check for explicit underground indicators
        if tags.get('tunnel') == 'yes':
            return True
        if tags.get('layer') == '-1':
            return True
        if tags.get('indoor') == 'no' and tags.get('level'):
            # Check if level indicates underground (contains negative levels)
            level_tag = tags.get('level', '')
            if ';' in level_tag:
                levels = level_tag.split(';')
                for level in levels:
                    try:
                        if float(level.strip()) < 0:
                            return True
                    except ValueError:
                        continue
        
        # If no clear underground indicators and has multi-level (like 0;1 or 1;2), 
        # it's likely above-ground elevated
        level_tag = tags.get('level', '')
        if ';' in level_tag:
            levels = level_tag.split(';')
            try:
                level_nums = [float(l.strip()) for l in levels]
                # If all levels are >= 0, it's likely above-ground
                if all(l >= 0 for l in level_nums):
                    return False
            except ValueError:
                pass
                
        # If escalator has "covered=yes" but no level/tunnel/layer info,
        # it's likely above-ground covered (like Tysons)
        if tags.get('covered') == 'yes' and not any([
            tags.get('tunnel'),
            tags.get('layer'), 
            tags.get('level'),
            tags.get('indoor')
        ]):
            return False
            
        # Default: include if unclear (conservative approach)
        return True

    def determine_escalator_direction(self, start_coord: Dict, end_coord: Dict, tags: Dict) -> tuple:
        """
        Determine which end of the escalator is the outside end.
        Returns (outside_coord, inside_coord) tuple.
        """
        # Strategy 1: Use level information if available
        level_tag = tags.get('level', '')
        if level_tag and ';' in level_tag:
            # Level tag format is often "start_level;end_level" or "0;-1" etc
            levels = level_tag.split(';')
            if len(levels) == 2:
                try:
                    start_level = float(levels[0].replace('_', '').strip())
                    end_level = float(levels[1].replace('_', '').strip())
                    
                    # Higher level number is usually outside (closer to surface)
                    if start_level > end_level:
                        return start_coord, end_coord  # start is outside
                    elif end_level > start_level:
                        return end_coord, start_coord  # end is outside
                except (ValueError, IndexError):
                    pass
        
        # Strategy 2: Use indoor tag combined with incline/conveying direction
        indoor = tags.get('indoor', '')
        incline = tags.get('incline', '')
        conveying = tags.get('conveying', '')
        
        # For escalators marked as not indoor, try to infer from incline
        if indoor == 'no':
            # If incline=down and conveying=forward, the way goes from outside to inside
            if incline == 'down' and conveying == 'forward':
                return start_coord, end_coord  # start is outside, going down to inside
            elif incline == 'down' and conveying == 'backward':
                return end_coord, start_coord  # end is outside, going down to inside
            elif incline == 'up' and conveying == 'forward':
                return end_coord, start_coord  # end is outside, going up from inside
            elif incline == 'up' and conveying == 'backward':
                return start_coord, end_coord  # start is outside, going up from inside
        
        # Strategy 3: Use tunnel/layer information
        tunnel = tags.get('tunnel', '')
        layer = tags.get('layer', '')
        
        if tunnel == 'yes' or layer == '-1':
            # This suggests underground, but we need to determine which end is more underground
            # For now, assume the way direction follows the logical flow
            if incline == 'down':
                return start_coord, end_coord  # going down from outside to inside
            elif incline == 'up':
                return end_coord, start_coord  # going up from inside to outside
        
        # Strategy 4: Default fallback - use the way that makes more sense
        # For outdoor escalators, typically they go from ground level to platform level
        # Most Metro escalators have incline tag indicating the direction
        if incline == 'down':
            # Way goes downward, so start is typically the higher/outside end
            return start_coord, end_coord
        elif incline == 'up':
            # Way goes upward, so end is typically the higher/outside end  
            return end_coord, start_coord
        
        # Final fallback: use conveying direction
        if conveying in ['forward', 'up']:
            return end_coord, start_coord  # end is outside
        elif conveying in ['backward', 'down']:
            return start_coord, end_coord  # start is outside
        
        # Ultimate fallback: use end as outside (original behavior)
        return end_coord, start_coord
    
    def find_station_name(self, node_refs: List[str], nodes: Dict, station_nodes: Dict) -> str:
        """Find the Metro station name associated with this escalator."""
        # First, check if any of the escalator's endpoint nodes have names
        for node_ref in [node_refs[0], node_refs[-1]] if len(node_refs) >= 2 else node_refs:
            if node_ref in station_nodes:
                node_data = station_nodes[node_ref]
                if 'name' in node_data['tags']:
                    return node_data['tags']['name']
        
        # If endpoint nodes don't have names, find the nearest named node
        if len(node_refs) >= 2:
            # Use escalator endpoints for distance calculation
            escalator_coords = [
                (nodes[node_refs[0]]['lat'], nodes[node_refs[0]]['lon']),
                (nodes[node_refs[-1]]['lat'], nodes[node_refs[-1]]['lon'])
            ]
        else:
            # Use single node
            escalator_coords = [(nodes[node_refs[0]]['lat'], nodes[node_refs[0]]['lon'])] if node_refs else []
        
        if not escalator_coords:
            return ""
        
        # Find the closest named station within reasonable distance (500m)
        min_distance = float('inf')
        closest_station = ""
        
        for station_id, station_data in station_nodes.items():
            station_coord = (station_data['lat'], station_data['lon'])
            
            # Calculate minimum distance to any escalator endpoint
            for esc_coord in escalator_coords:
                distance = self.haversine_distance(esc_coord[0], esc_coord[1], station_coord[0], station_coord[1])
                
                if distance < min_distance and distance < 0.5:  # Within 500m
                    min_distance = distance
                    if 'name' in station_data['tags']:
                        closest_station = station_data['tags']['name']
        
        return closest_station
    
    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate the great circle distance between two points in kilometers."""
        # Convert decimal degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Radius of earth in kilometers
        r = 6371
        return c * r
        
    def calculate_solar_alignments(self, lat: float, lon: float, azimuth: float) -> List[pd.Timestamp]:
        """Calculate when the sun aligns with the escalator direction (shines straight down)."""
        try:
            # Escalator parameters
            ESCALATOR_ELEVATION = 30  # degrees below horizontal
            ESCALATOR_AZIMUTH = azimuth
            
            # Create location for solar calculations
            location = pvlib.location.Location(latitude=lat, longitude=lon, tz='America/New_York')
            
            # Generate times for the next year (every minute)
            times = pd.date_range(
                start='2025-01-01', 
                end='2025-12-31', 
                freq='1min', 
                tz=location.tz
            )
            
            # Calculate solar position
            solar_position = location.get_solarposition(times)
            
            # Find times when sun aligns with escalator
            # Sun should be at the same azimuth as the escalator direction and at 30° elevation
            target_azimuth = ESCALATOR_AZIMUTH
            
            # Find alignments within tolerance
            azimuth_tolerance = 5  # degrees
            elevation_tolerance = 15  # degrees
            
            alignment_mask = (
                (np.abs(solar_position['azimuth'] - target_azimuth) < azimuth_tolerance) |
                (np.abs(solar_position['azimuth'] - target_azimuth + 360) < azimuth_tolerance) |
                (np.abs(solar_position['azimuth'] - target_azimuth - 360) < azimuth_tolerance)
            ) & (
                np.abs(solar_position['elevation'] - ESCALATOR_ELEVATION) < elevation_tolerance
            ) & (
                solar_position['elevation'] > 0  # Sun must be above horizon
            )
            
            return times[alignment_mask].tolist()
            
        except Exception as e:
            print(f"Error calculating solar alignments for escalator: {e}")
            return []

    def save_to_parquet(self, escalators: List[Dict], base_filename: str) -> None:
        """Save escalator data to normalized Parquet files."""
        
        # Generate Parquet filenames
        escalators_filename = base_filename.replace('.csv', '_escalators.parquet') if base_filename.endswith('.csv') else f"{base_filename}_escalators.parquet"
        alignments_filename = base_filename.replace('.csv', '_solar_alignments.parquet') if base_filename.endswith('.csv') else f"{base_filename}_solar_alignments.parquet"
        
        print(f"Saving normalized data to {escalators_filename} and {alignments_filename}...")
        
        # Prepare escalators table
        escalator_rows = []
        for escalator in escalators:
            escalator_rows.append({
                'id': escalator['id'],
                'name': escalator['name'] or f"Escalator {escalator['id']}",
                'type': 'way',
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
                'node_count': len(escalator.get('node_refs', [])),
                'azimuth': escalator.get('azimuth'),
                'top_lat': escalator.get('top_lat'),
                'top_lon': escalator.get('top_lon'),
                'station_name': escalator.get('station_name', '')
            })
        
        pd.DataFrame(escalator_rows).to_parquet(escalators_filename, index=False)
        print(f"Successfully saved {len(escalator_rows)} escalators to {escalators_filename}")
        
        # Prepare solar alignments table
        alignment_rows = []
        for escalator in escalators:
            escalator_id = escalator['id']
            for dt in escalator.get('solar_alignments', []):
                alignment_rows.append({
                    'escalator_id': escalator_id,
                    'station_name': escalator.get('station_name', ''),
                    'alignment_datetime': dt,
                    'year': dt.year,
                    'month': dt.month,
                    'day': dt.day,
                    'hour': dt.hour,
                    'minute': dt.minute,
                    'timezone': str(dt.tzinfo),
                })
        
        pd.DataFrame(alignment_rows).to_parquet(alignments_filename, index=False)
        print(f"Successfully saved {len(alignment_rows)} solar alignments to {alignments_filename}")

        
    def load_escalators(self, bbox: Optional[str] = None, output_file: str = "src/data/dc_metro_escalators.csv") -> List[Dict]:
        """Main method to load escalator data."""
        try:
            # Build and execute query
            query = self.build_overpass_query(bbox)
            xml_data = self.fetch_osm_data(query)
            
            # Parse and process data
            escalators = self.parse_osm_xml(xml_data)
            
            if escalators:
                self.save_to_parquet(escalators, output_file)
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
    
    args = parser.parse_args()
    
    loader = OSMEscalatorLoader()
    escalators = loader.load_escalators(bbox=args.bbox, output_file=args.output)

if __name__ == "__main__":
    main()
