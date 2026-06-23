from dataclasses import dataclass



from dataclasses import dataclass

@dataclass
class AdventureStage:
    name: str

    @property
    def location_name(self) -> str:
        return f"{self.name} - Complete"

    @property
    def location_names(self) -> list[str]:
        return [
            f"{self.location_name}",
            f"{self.location_name} 2"
        ]

    def get_location_names(self, num: int) -> list[str]:
        if num == 1:
            return [self.location_name]
        return self.location_names[:num]

    @property
    def unlock_name(self) -> str:
        return f"Unlock - {self.name}"


stages = [
    #  EU 0x122bc5
    AdventureStage("SOL Laboratory 1"),
    AdventureStage("SOL Laboratory 2"),
    AdventureStage("SOL Laboratory 3"),
    AdventureStage("SOL Laboratory 4"),
    #  EU 0x122bc6
    AdventureStage("SOL Laboratory 5"),
    AdventureStage("Secret Storage 1"),
    AdventureStage("Secret Storage 2"),
    AdventureStage("Secret Storage 3"),
    #  EU 0x122bc7
    AdventureStage("Secret Storage 4"),
    AdventureStage("Secret Storage 5"),
    AdventureStage("Secret Storage 6"),
    AdventureStage("Secret Storage 7"),
    #  EU 0x122bc8
    AdventureStage("Secret Storage 8"),
    AdventureStage("Secret Storage 9"),
    AdventureStage("Secret Storage 10"),
    AdventureStage("Secret Storage 11"),
    #  EU 0x122bc9
    AdventureStage("Secret Storage 12"),
    AdventureStage("Secret Storage 13"),
    AdventureStage("Secret Storage 14"),
    AdventureStage("Secret Storage 15"),
    #  EU 0x122bca
    AdventureStage("Secret Storage 16"),
    AdventureStage("Secret Storage 17"),
    AdventureStage("Secret Storage 18"),
    AdventureStage("Secret Storage 19"),
    #  EU 0x122bcb
    AdventureStage("Secret Storage 20"),
    AdventureStage("Huge Storage 1"),
    AdventureStage("Huge Storage 2"),
    AdventureStage("Huge Storage 3"),
    #  EU 0x122bcc
    AdventureStage("Huge Storage 4"),
    AdventureStage("Huge Storage 5"),
    AdventureStage("Phobos Mobile No. 1: Phobos Train"),
    AdventureStage("Phobos Mobile No. 2: Phobos Jet"),
    #  EU 0x122bcd
    AdventureStage("Phobos Mobile No. 3: Phobos Drill"),
    AdventureStage("Phobos Mobile No. 4: Phobos Sub"),
    AdventureStage("Phobos Mobile No. 5: Phobos Walker"),
    AdventureStage("Phobos Secret Fort: Phobosphere"),
    #  EU 0x122bce
    # AdventureStage("Mr. Who's Den"),
]


def determine_stage_location_count():
    return 2
