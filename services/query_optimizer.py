import time
import re
from sqlalchemy import text
from models.user import db
from models.performance_log import PerformanceLog
from services.query_analyser import QueryAnalyserService

class QueryOptimizerService:
    @staticmethod
    def measure_execution_time(query):
        """
        Executes a SELECT query and measures its execution time in milliseconds.
        """
        start_time = time.time()
        try:
            db.session.execute(text(query))
            db.session.commit() # To ensure we aren't just caching
        except Exception as e:
            return -1, str(e)
            
        end_time = time.time()
        return (end_time - start_time) * 1000, None  # milliseconds

    @staticmethod
    def generate_suggestions(query):
        """
        Analyzes a query and its EXPLAIN plan to suggest optimizations like indexes.
        """
        analysis = QueryAnalyserService.analyze_query(query)
        if not analysis.get("success"):
            return analysis
            
        plan = analysis.get("plan", [])
        suggestions = []
        
        # Very rudimentary SQL parsing to find columns for indexing
        # In a real system, use a proper SQL parser (like sqlparse)
        
        for row in plan:
            table_name = row.get("table")
            access_type = row.get("type", "").upper()
            extra = row.get("Extra", "")
            
            if not table_name:
                continue
                
            # If full table scan is detected, try to find the WHERE or JOIN condition
            if access_type == 'ALL':
                # Attempt to extract WHERE clause columns for this table
                where_match = re.search(r'WHERE\s+(.*?)(?:ORDER|GROUP|LIMIT|$)', query, re.IGNORECASE)
                if where_match:
                    conditions = where_match.group(1)
                    # Look for table.column or just column if it's a simple query
                    # This is highly simplified for demonstration purposes
                    cols = re.findall(rf'\b(?:{table_name}\.)?([a-zA-Z0-9_]+)\s*(?:=|!=|<|>|LIKE|IN)', conditions, re.IGNORECASE)
                    
                    if cols:
                        col_to_index = cols[0]
                        index_name = f"idx_{table_name}_{col_to_index}"
                        suggestion = {
                            "type": "index",
                            "description": f"Full table scan detected on '{table_name}'. Consider adding an index on '{col_to_index}'.",
                            "sql": f"CREATE INDEX {index_name} ON {table_name}({col_to_index});",
                            "table": table_name,
                            "column": col_to_index
                        }
                        # Prevent duplicate suggestions
                        if not any(s['sql'] == suggestion['sql'] for s in suggestions):
                            suggestions.append(suggestion)

        # If SELECT * is used
        if re.search(r'SELECT\s+\*', query, re.IGNORECASE):
            suggestions.append({
                "type": "rewrite",
                "description": "Avoid using 'SELECT *'. Specify the exact columns you need to reduce data transfer.",
                "sql": None
            })

        return {
            "success": True,
            "plan": plan,
            "warnings": analysis.get("warnings", []),
            "suggestions": suggestions
        }

    @staticmethod
    def apply_optimization(optimization_sql, original_query):
        """
        Safely applies an optimization (e.g., CREATE INDEX) and logs the performance improvement.
        """
        if not optimization_sql.strip().upper().startswith("CREATE INDEX"):
            return {"success": False, "error": "Only CREATE INDEX operations are permitted automatically."}
            
        # Measure before
        time_before, error = QueryOptimizerService.measure_execution_time(original_query)
        if error:
            return {"success": False, "error": f"Failed to execute original query: {error}"}
            
        try:
            # Apply optimization
            db.session.execute(text(optimization_sql))
            db.session.commit()
            
            # Measure after
            time_after, error = QueryOptimizerService.measure_execution_time(original_query)
            if error:
                return {"success": False, "error": f"Failed to execute query after optimization: {error}"}
                
            improvement = 0
            if time_before > 0:
                improvement = ((time_before - time_after) / time_before) * 100
                
            # Log the performance
            log = PerformanceLog(
                query_text=original_query,
                execution_time_before=time_before,
                execution_time_after=time_after,
                optimization_applied=optimization_sql,
                improvement_percentage=improvement
            )
            db.session.add(log)
            db.session.commit()
            
            return {
                "success": True,
                "message": "Optimization applied successfully.",
                "time_before": round(time_before, 4),
                "time_after": round(time_after, 4),
                "improvement": round(improvement, 2)
            }
            
        except Exception as e:
            db.session.rollback()
            return {"success": False, "error": str(e)}
