from mmu import MMU


class ClockMMU(MMU):
    def __init__(self, frames):
        # TODO: Constructor logic for EscMMU
        # Number of physical frames in memory
        self.number_frames = frames
        # List of frames that implement "clock" structure
        self.frames = []
        #  Clock hand pointer
        self.clock_hand = 0
        # Statistics for analysis
        self.page_faults = 0
        self.disk_reads = 0
        self.disk_writes = 0
        # Debug mode flag
        self.debug = False

    def set_debug(self):
        # TODO: Implement the method to set debug mode
        self.debug = True

    def reset_debug(self):
        # TODO: Implement the method to reset debug mode
        self.debug = False

    def read_memory(self, page_number):
        # TODO: Implement the method to read memory
        self.access_memory(page_number, is_write=False)

    def write_memory(self, page_number):
        # TODO: Implement the method to write memory
        self.access_memory(page_number, is_write=True)

    def get_total_disk_reads(self):
        # TODO: Implement the method to get total disk reads
        return self.disk_reads

    def get_total_disk_writes(self):
        # TODO: Implement the method to get total disk writes
        return self.disk_writes

    def get_total_page_faults(self):
        # TODO: Implement the method to get total page faults
        return self.page_faults
    
    def access_memory(self, page_number, is_write):
        
        # Page HIT (in memory)
        for frame in self.frames:
            if frame["page"] == page_number:
                # Set reference bit to 1
                frame["reference"] = 1
                if is_write:
                    frame["dirty"] = True
                if self.debug:
                    print(f"HIT: Page {page_number}. Dirty: {frame['dirty']}. Reference: 1")
                return
        
        # Page FAULT (not in memory)
        self.page_faults += 1
        self.disk_reads += 1
        if self.debug:
            print(f"FAULT: Page {page_number}")

        # Append frame if there is space
        if len(self.frames) < self.number_frames:
            self.frames.append({"page": page_number, "dirty": is_write, "reference": 1})
            if self.debug:
                print(f"LOADED: Page {page_number}. Dirty: {is_write}. Reference: 1 (Free slot)")
            return
        
        # Remove page with clock algorithm
        removing_page_index = self.find_removing_page()
        removing_page = self.frames[removing_page_index]

        if removing_page["dirty"]:
            self.disk_writes += 1
            if self.debug:
                print(f"REMOVING: Dirty {removing_page['page']}")
        else:
            if self.debug:
                print(f"REMOVING: Clean {removing_page['page']}")

        # Replace removed page with new page
        self.frames[removing_page_index] = {"page": page_number, "dirty": is_write, "reference": 1}
        if self.debug:
            print(f"LOADED: Page {page_number}. Dirty: {is_write}. Reference: 1 (Replaced page)")

    def find_removing_page(self):
        # If reference bit 0, remove page. If 1, set to 0 and move clock hand
        while True:
            frame = self.frames[self.clock_hand]
            if frame["reference"] == 0:
                removing_page_index = self.clock_hand
                # Advance clock hand
                self.clock_hand = (self.clock_hand + 1) % self.number_frames
                return removing_page_index
            else:
                # Give second chance (set reference from 1 to 0)
                frame["reference"] = 0
                if self.debug:
                    print(f"SECOND CHANCE: Page {frame['page']}. Reference: 0")
                self.clock_hand = (self.clock_hand + 1) % self.number_frames