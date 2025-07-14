import os
import time
import multiprocessing
from multiprocessing import Manager
import threading

def print_grid(grid):
    for i in range(9):
        if i % 3 == 0 and i != 0:
            print("-"*21)
        for j in range(9):
            if j % 3 == 0 and j != 0:
                print("| ", end='')
            print(str(grid[i][j]) if grid[i][j] != 0 else '.', end=' ')
        print()

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def find_empty_cell(grid):
    for i in range(9):
        for j in range(9):
            if grid[i][j] == 0:
                return i, j
    return None

def is_valid(grid, row, col, num):
    # Check row
    if num in grid[row]:
        return False
    # Check column
    if num in (grid[i][col] for i in range(9)):
        return False
    # Check box
    start_row = row - row % 3
    start_col = col - col % 3
    for i in range(3):
        for j in range(3):
            if grid[start_row + i][start_col + j] == num:
                return False
    return True

def get_possible_numbers(grid, row, col):
    numbers = set(range(1, 10))
    numbers -= set(grid[row])  # Remove numbers present in the row
    numbers -= set(grid[i][col] for i in range(9))  # Remove numbers present in the column
    start_row = row - row % 3
    start_col = col - col % 3
    # Remove numbers present in the 3x3 box
    numbers -= set(
        grid[start_row + i][start_col + j]
        for i in range(3) for j in range(3)
    )
    return numbers

def count_constraints(grid, row, col, num):
    count = 0
    for i in range(9):
        if grid[row][i] == 0:
            count += 1
        if grid[i][col] == 0:
            count += 1
    start_row = row - row % 3
    start_col = col - col % 3
    for i in range(3):
        for j in range(3):
            if grid[start_row + i][start_col + j] == 0:
                count += 1
    return count

def solve_sudoku(grid, queue=None, progress=None, worker_id=None, stop_event=None, stats=None):
    if stop_event and stop_event.is_set():
        return False
    empty_cell = find_empty_cell(grid)
    if not empty_cell:
        return True
    row, col = empty_cell
    possible_numbers = get_possible_numbers(grid, row, col)
    if not possible_numbers:
        if stats is not None:
            stats['backtracks'] += 1
        return False
    possible_numbers = sorted(possible_numbers, key=lambda num: count_constraints(grid, row, col, num))
    for num in possible_numbers:
        if stop_event and stop_event.is_set():
            return False
        if is_valid(grid, row, col, num):
            grid[row][col] = num
            if stats is not None:
                stats['attempts'] += 1
            if progress is not None:
                progress['grid'] = [row[:] for row in grid]
            if solve_sudoku(grid, queue, progress, worker_id, stop_event, stats):
                if queue and queue.empty():
                    queue.put([row[:] for row in grid])
                return True
            grid[row][col] = 0
            if stats is not None:
                stats['backtracks'] += 1
    return False

def worker(grid, queue, progress, worker_id, stop_event, stats, initial_cell):
    grid_copy = [row[:] for row in grid]
    row, col, possible_numbers = initial_cell
    possible_numbers = sorted(possible_numbers, key=lambda num: count_constraints(grid_copy, row, col, num))
    for num in possible_numbers:
        if stop_event.is_set():
            break
        if is_valid(grid_copy, row, col, num):
            grid_copy[row][col] = num
            if stats is not None:
                stats['attempts'] += 1
            if progress is not None:
                progress['grid'] = [row[:] for row in grid_copy]
            if solve_sudoku(grid_copy, queue, progress, worker_id, stop_event, stats):
                stop_event.set()
                if queue.empty():
                    queue.put([row[:] for row in grid_copy])
                break
            grid_copy[row][col] = 0
            if stats is not None:
                stats['backtracks'] += 1

def display_progress(progress, stop_event):
    while not stop_event.is_set():
        clear_screen()
        print("Solving Sudoku...")
        if 'grid' in progress:
            print_grid(progress['grid'])
        else:
            print("Initializing...")
        time.sleep(0.5)
    clear_screen()
    if 'grid' in progress:
        print("Solved Sudoku:")
        print_grid(progress['grid'])
    else:
        print("No solution found.")

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    save_file = os.path.join(script_dir, "sudoku_save.txt")

    if not os.path.exists(save_file):
        print(f"Puzzle file '{save_file}' not found.")
        return

    with open(save_file, 'r') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    if len(lines) != 9:
        print("Puzzle file must contain 9 lines of numbers.")
        return

    grid = []
    for line in lines:
        parts = line.split()
        if len(parts) != 9:
            print("Each line must contain 9 numbers.")
            return
        grid.append([int(x) for x in parts])

    clear_screen()
    print("Initial Sudoku:")
    print_grid(grid)
    time.sleep(1)
    start_time = time.time()

    manager = Manager()
    queue = manager.Queue()
    progress = manager.dict()
    progress['grid'] = [row[:] for row in grid]
    stats = manager.dict()
    stats['attempts'] = 0
    stats['backtracks'] = 0
    stop_event = multiprocessing.Event()

    # Preprocessing: Find cells with the least possibilities
    empty_cells = []
    for i in range(9):
        for j in range(9):
            if grid[i][j] == 0:
                possible_numbers = get_possible_numbers(grid, i, j)
                empty_cells.append((i, j, possible_numbers))
    empty_cells.sort(key=lambda x: len(x[2]))
    if not empty_cells:
        print("Sudoku already solved!")
        return

    num_workers = min(9, multiprocessing.cpu_count(), len(empty_cells))
    processes = []

    # Start display thread
    display_thread = threading.Thread(target=display_progress, args=(progress, stop_event))
    display_thread.start()

    # Start worker processes
    for worker_id in range(num_workers):
        initial_cell = empty_cells[worker_id]
        p = multiprocessing.Process(target=worker, args=(
            grid, queue, progress, worker_id, stop_event, stats, initial_cell))
        processes.append(p)
        p.start()

    for p in processes:
        p.join()

    stop_event.set()
    display_thread.join()

    end_time = time.time()
    elapsed_time = end_time - start_time

    clear_screen()
    if not queue.empty():
        solved_grid = queue.get()
        print("Sudoku solved:")
        print_grid(solved_grid)
        with open(save_file, 'w') as f:
            for row in solved_grid:
                f.write(' '.join(map(str, row)) + '\n')
    else:
        print("No solution exists.")

    # Display statistics
    print("\nStatistics:")
    print(f"Time taken: {elapsed_time:.2f} seconds")
    print(f"Total attempts: {stats['attempts']}")
    print(f"Total backtracks: {stats['backtracks']}")
    if stats['attempts'] > 0:
        print(f"Backtrack ratio: {stats['backtracks']/stats['attempts']:.2f}")
    else:
        print("No attempts were made.")

    print("\nSolved grid saved to sudoku_save.txt")

if __name__ == "__main__":
    main()
