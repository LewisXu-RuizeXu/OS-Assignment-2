from mmu import MMU

class LruMMU(MMU):
    def __init__(self, frames):
        # TODO: Constructor logic for LruMMU
        # Number of physical frames in memory
        self.number_frames = frames
        # Dictionary that tracks the loaded pages
        self.frames = {}
        # Statistics for analysis
        self.page_faults = 0
        self.disk_reads = 0
        self.disk_writes = 0
        # Debug mode flag
        self.debug = False
        # Counter to track recency
        self.recency_tracker = 0

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
        #  Increase recency tracker on each access
        self.recency_tracker += 1

        # Page HIT (in memory)
        if page_number in self.frames:
            if is_write:
                self.frames[page_number]["dirty"] = True
            self.frames[page_number]["last_used"] = self.recency_tracker
            if self.debug:
                print(f"HIT: Page {page_number}. Dirty: {self.frames[page_number]['dirty']}")
            return
        
        # Page FAULT (not in memory)
        self.page_faults += 1
        self.disk_reads += 1
        if self.debug:
            print(f"FAULT: Page {page_number}")

        # If memory is full, remove least recently used page
        if len(self.frames) >= self.number_frames:
            # Find least used page
            removing_page = min(self.frames, key=lambda p: self.frames[p]["last_used"])
            removing_page_dirty = self.frames[removing_page]["dirty"]

            if removing_page_dirty:
                self.disk_writes += 1
                if self.debug:
                    print(f"REMOVING: Dirty {removing_page}")
            else:
                if self.debug:
                    print(f"REMOVING: Clean {removing_page}")

            del self.frames[removing_page]

        #  Load new page into memory
        self.frames[page_number] = {"dirty": is_write, "last_used": self.recency_tracker}
        if self.debug:
            print(f"LOADED: Page {page_number}. Dirty: {is_write}")

