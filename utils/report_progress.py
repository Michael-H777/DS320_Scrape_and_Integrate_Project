import os 
import curses 
from itertools import count
from time import sleep, time

'''
    This function create a screen for multi-line report 
'''


class EmergencyRestart(Exception):
    pass 


def report_progress(process_list, message_q_list, worker_counts, result_dir=None, restart=False, sleep_time=0, check_alive=False, refresh=0.5):

    start_time = time()
    # lists to store messages 
    message_list = [''] * len(process_list)

    for index in range(1, len(worker_counts)):
        worker_counts[index] += worker_counts[index - 1]

    if result_dir:
        already_scraped = len(os.listdir(result_dir))

    # initialzie new screen for reporting 
    report_progress = curses.initscr()
    curses.noecho()
    curses.cbreak()
    # report progress 
    while any([item.is_alive() for item in process_list]):
        sleep(0.2)
        # restart if needed 
        if restart and any([(not item1.is_alive() and 'completed' not in item2) 
                        for item1, item2 in zip(process_list, message_list)]):
            [item.terminate() for item in process_list]
            raise EmergencyRestart

        sleep(refresh)
        report_progress.addstr(0, 0, 'progress report: ')
        str_line = count(2)
        for index in range(len(message_list)):
            current_q = message_q_list[index]
            current_p = process_list[index]
            # we only care about the latest message 
            if current_q.qsize() > 0:
                current_msg = [current_q.get() for _ in range(current_q.qsize())][-1] 
                message_list[index] = current_msg
            # if theres no new messages, keep the previous one 
            else:
                current_msg = message_list[index]

            # aesthetic
            if index in worker_counts:
                next(str_line)
            # actual report 

            report_str = current_msg
            if check_alive:
                alive_status = 'process is alive' if current_p.is_alive() else 'process is dead'
                report_str += f', {alive_status}'

            report_progress.addstr(next(str_line), 0, f'{report_str}{"  "*50}')

        # seperator
        next(str_line)
        # calcualte time elapsed
        time_used = round(time() - start_time)
        
        time_str = f'{time_used//3600}:{str((time_used%3600)//60):0>2}:{str(time_used%60):0>2}'
        if result_dir:
            total_scraped = len(os.listdir(result_dir)) - already_scraped
            report_progress.addstr(next(str_line), 0, f'acquired {total_scraped} entities, time elapsed {time_str} {" "*20}')
        else:
            report_progress.addstr(next(str_line), 0, f'time elapsed {time_str} {" "*20}')
        # refresh screen to show msgs 
        report_progress.refresh()

    if sleep_time:
        sleep(sleep_time)
    # after all processes have been termianted, quit curses
    curses.echo()
    curses.nocbreak()
    curses.endwin()

    print(f'total time: {time_str}')
    