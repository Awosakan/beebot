import heapq
import math
import numpy as np

class AStarPlanner:
    """
    Yerel Costmap üzerinde otonom aracın yerel minimumlara (Local Minima) 
    düşmesini engelleyen A* (A-Star) global planlayıcı algoritması.
    Araç APF (Yapay Potansiyel Alan) ile sıkıştığında veya karmaşık 
    engellerle karşılaştığında güvenli bir rotadan 'havuç' (carrot point) üretir.
    """
    def __init__(self, resolution: float = 0.25):
        self.resolution = resolution

    def heuristic(self, a, b):
        return math.sqrt((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2)

    def plan(self, start_idx: tuple, goal_idx: tuple, grid: np.ndarray, threshold: int = 50) -> list:
        """
        Grid üzerinde start_idx'den goal_idx'e en kısa ve güvenli yolu bulur.
        Döndürülen liste, geçiş hücrelerinin (row, col) koordinatlarıdır.
        """
        max_r, max_c = grid.shape
        
        # Başlangıç veya Hedef grid dışındaysa kırp
        if not (0 <= start_idx[0] < max_r and 0 <= start_idx[1] < max_c):
            return []
            
        gr = max(0, min(goal_idx[0], max_r - 1))
        gc = max(0, min(goal_idx[1], max_c - 1))
        goal_idx = (gr, gc)

        # Eğer hedef bir engelin içindeyse, en yakın boş noktayı bulmaya çalış (Basit fallback)
        if grid[goal_idx[0], goal_idx[1]] >= threshold:
            for dr in [-2, -1, 0, 1, 2]:
                for dc in [-2, -1, 0, 1, 2]:
                    nr, nc = goal_idx[0] + dr, goal_idx[1] + dc
                    if 0 <= nr < max_r and 0 <= nc < max_c and grid[nr, nc] < threshold:
                        goal_idx = (nr, nc)
                        break

        open_set = []
        heapq.heappush(open_set, (0.0, start_idx))
        came_from = {}
        g_score = {start_idx: 0.0}
        
        # 8-yönlü hareket
        dirs = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]

        while open_set:
            current_f, current = heapq.heappop(open_set)

            if current == goal_idx:
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.reverse()
                return path

            for dr, dc in dirs:
                neighbor = (current[0] + dr, current[1] + dc)
                if 0 <= neighbor[0] < max_r and 0 <= neighbor[1] < max_c:
                    cell_cost = grid[neighbor[0], neighbor[1]]
                    
                    if cell_cost >= threshold:
                        continue
                    
                    # Çapraz hareket maliyeti 1.414, düz hareket 1.0
                    move_cost = 1.414 if dr != 0 and dc != 0 else 1.0
                    
                    # Engellerin yakınından geçerken ek ceza maliyeti (Duvarlardan uzak dur)
                    penalty = (cell_cost / 100.0) * 3.0 

                    tentative_g_score = g_score[current] + move_cost + penalty

                    if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                        came_from[neighbor] = current
                        g_score[neighbor] = tentative_g_score
                        f_score = tentative_g_score + self.heuristic(neighbor, goal_idx)
                        heapq.heappush(open_set, (f_score, neighbor))
                        
        return []
