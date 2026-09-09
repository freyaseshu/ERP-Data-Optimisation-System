import re
from sqlalchemy import text
from models.user import db

class QueryAnalyserService:
    @staticmethod
    def is_safe_query(query):
        """
        Validates if a query is a safe SELECT statement and doesn't contain destructive keywords.
        """
        # Basic validation: ensure it starts with SELECT and doesn't have multiple statements
        query = query.strip()
        if not re.match(r'^SELECT\b', query, re.IGNORECASE):
            return False, "Only SELECT queries are allowed for analysis."
            
        # Check for destructive keywords
        destructive_keywords = [
            r'\bDROP\b', r'\bDELETE\b', r'\bTRUNCATE\b', r'\bALTER\b', 
            r'\bUPDATE\b', r'\bINSERT\b', r'\bCREATE\b', r'\bGRANT\b', 
            r'\bREVOKE\b', r'\bEXEC\b', r'\bCALL\b'
        ]
        
        for keyword in destructive_keywords:
            if re.search(keyword, query, re.IGNORECASE):
                return False, f"Destructive keyword '{keyword.replace(r'\\b', '').replace('\\b', '')}' detected. Query rejected."
                
        # Check for multiple statements (semicolon injection)
        if ';' in query.rstrip(';'):
            return False, "Multiple SQL statements are not allowed."
            
        return True, "Safe query."

    @staticmethod
    def analyze_query(query):
        """
        Executes EXPLAIN on the given query and returns the execution plan.
        """
        is_safe, message = QueryAnalyserService.is_safe_query(query)
        if not is_safe:
            return {"success": False, "error": message}

        try:
            # Run EXPLAIN format=json for easier parsing, or standard EXPLAIN
            # Standard EXPLAIN gives columns: id, select_type, table, partitions, type, possible_keys, key, key_len, ref, rows, filtered, Extra
            explain_query = text(f"EXPLAIN {query}")
            result = db.session.execute(explain_query)
            
            plan = []
            warnings = []
            
            for row in result:
                # Convert row proxy to dict
                # Note: row._mapping provides dict-like access in newer SQLAlchemy versions
                row_dict = dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
                
                plan.append(row_dict)
                
                # Analyze for potential issues based on EXPLAIN output
                access_type = row_dict.get('type', '')
                extra = row_dict.get('Extra', '')
                rows_examined = row_dict.get('rows', 0)
                
                # Highlighting possible performance problems
                if access_type == 'ALL':
                    warnings.append(f"Full table scan detected on table '{row_dict.get('table')}'. Consider adding an index.")
                
                if 'Using temporary' in extra:
                    warnings.append(f"Temporary table used for query on table '{row_dict.get('table')}'. This can be slow.")
                    
                if 'Using filesort' in extra:
                    warnings.append(f"Filesort used on table '{row_dict.get('table')}'. Consider an index for the ORDER BY clause.")
                    
                if isinstance(rows_examined, int) and rows_examined > 1000:
                    warnings.append(f"Large number of rows ({rows_examined}) scanned on table '{row_dict.get('table')}'.")

            return {
                "success": True,
                "plan": plan,
                "warnings": warnings,
                "original_query": query
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
